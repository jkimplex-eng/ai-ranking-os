import json
import time
from collections.abc import Generator
from threading import Event, Lock
from time import perf_counter
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from query_executor.dispatcher import Dispatcher
from query_executor.executor import InMemoryTelemetry, execute_plan
from query_executor.models import (
    QueryExecutionHistory,
    QueryExecutionMetric,
    QueryProviderMetric,
)
from query_executor.schemas import ExecutionPlan, ExecutorState, StepState

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture
def client() -> Generator[TestClient]:
    Base.metadata.create_all(test_engine)

    def override_get_db() -> Generator[Session]:
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)


def plan(mode: str, providers: list[str], **step_options: Any) -> ExecutionPlan:
    return ExecutionPlan.model_validate(
        {
            "plan_id": f"{mode.lower()}-plan",
            "execution_mode": mode,
            "steps": [
                {
                    "id": f"step-{index}",
                    "provider": provider,
                    "input": {"query": "hello"},
                    **step_options,
                }
                for index, provider in enumerate(providers, start=1)
            ],
        }
    )


def test_single_execution_and_telemetry() -> None:
    telemetry = InMemoryTelemetry()
    result = execute_plan(
        "single-execution",
        plan("SINGLE", ["codex"]),
        Dispatcher(),
        telemetry=telemetry,
    )

    assert result.state == ExecutorState.COMPLETED
    assert result.output == {"provider": "codex", "content": "hello"}
    assert result.results[0].attempts == 1
    assert result.telemetry["event_count"] >= 4


def test_parallel_execution_is_concurrent() -> None:
    active = 0
    max_active = 0
    lock = Lock()

    def provider(payload: dict[str, Any], cancellation: Event) -> dict[str, Any]:
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.03)
        with lock:
            active -= 1
        return payload

    dispatcher = Dispatcher({"one": provider, "two": provider})
    result = execute_plan(
        "parallel-execution",
        plan("PARALLEL", ["one", "two"]),
        dispatcher,
    )

    assert result.state == ExecutorState.COMPLETED
    assert len(result.output) == 2
    assert max_active == 2


def test_ensemble_collects_consensus() -> None:
    def same_provider(payload: dict[str, Any], cancellation: Event) -> dict[str, Any]:
        return {"answer": 42}

    dispatcher = Dispatcher({"one": same_provider, "two": same_provider})
    result = execute_plan(
        "ensemble-execution",
        plan("ENSEMBLE", ["one", "two"]),
        dispatcher,
    )

    assert result.state == ExecutorState.COMPLETED
    assert result.output["consensus"] == {"answer": 42}
    assert result.output["votes"] == 2


def test_fallback_retry_and_skipping() -> None:
    attempts = 0
    delays: list[float] = []

    def flaky(payload: dict[str, Any], cancellation: Event) -> dict[str, Any]:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("provider unavailable")

    def successful(payload: dict[str, Any], cancellation: Event) -> dict[str, Any]:
        return {"provider": "backup"}

    dispatcher = Dispatcher({"primary": flaky, "backup": successful, "unused": successful})
    result = execute_plan(
        "fallback-execution",
        plan(
            "FALLBACK",
            ["primary", "backup", "unused"],
            retries=2,
            retry_base_seconds=1,
        ),
        dispatcher,
        sleep=delays.append,
    )

    assert result.state == ExecutorState.COMPLETED
    assert attempts == 3
    assert delays == [1, 2]
    assert result.results[0].state == StepState.FAILED
    assert result.results[1].state == StepState.COMPLETED
    assert result.results[2].state == StepState.SKIPPED
    assert result.output == {"provider": "backup"}


def test_timeout_and_preemptive_cancellation() -> None:
    def slow(payload: dict[str, Any], cancellation: Event) -> None:
        time.sleep(0.05)

    timeout_dispatcher = Dispatcher({"slow": slow})
    timeout_result = execute_plan(
        "timeout-execution",
        plan("SINGLE", ["slow"], timeout=0.005, retries=0),
        timeout_dispatcher,
    )
    assert timeout_result.state == ExecutorState.TIMED_OUT
    assert timeout_result.results[0].state == StepState.TIMED_OUT

    cancellation = Event()
    cancellation.set()
    cancelled = execute_plan(
        "cancelled-execution",
        plan("SINGLE", ["codex"]),
        Dispatcher(),
        cancellation=cancellation,
    )
    assert cancelled.state == ExecutorState.CANCELLED
    assert cancelled.results[0].state == StepState.CANCELLED


def test_integration_run_get_metrics_and_router_aliases(client: TestClient) -> None:
    response = client.post(
        "/executor/run",
        json={
            "execution_plan": {
                "plan_id": "router-plan",
                "request_id": "router-request",
                "strategy": "parallel",
                "providers": {
                    "codex": {"input": {"query": "answer"}},
                    "qwen": {"input": {"query": "answer"}},
                },
            }
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "COMPLETED"
    assert body["mode"] == "PARALLEL"

    stored = client.get(f"/executor/{body['execution_id']}")
    assert stored.status_code == 200
    assert stored.json() == body

    with TestingSession() as session:
        executions = session.scalar(
            select(func.count()).select_from(QueryExecutionHistory)
        )
        metrics = session.scalar(select(func.count()).select_from(QueryExecutionMetric))
        providers = session.scalar(select(func.count()).select_from(QueryProviderMetric))
    assert executions == 1
    assert metrics == 3
    assert providers == 2


def test_streaming_ndjson(client: TestClient) -> None:
    response = client.post(
        "/executor/stream",
        json={"mode": "SINGLE", "providers": ["codex"]},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    events = [json.loads(line) for line in response.text.splitlines()]
    assert [event["event"] for event in events] == [
        "execution_started",
        "step_result",
        "execution_finished",
    ]


def test_invalid_plan_and_missing_execution(client: TestClient) -> None:
    response = client.post(
        "/executor/run",
        json={"mode": "SINGLE", "providers": ["codex", "qwen"]},
    )
    assert response.status_code == 422
    assert client.get("/executor/missing").status_code == 404


def test_benchmark_executor_overhead() -> None:
    execution_plan = plan("SINGLE", ["echo"])
    dispatcher = Dispatcher()
    started = perf_counter()
    for index in range(500):
        result = execute_plan(f"benchmark-{index}", execution_plan, dispatcher)
        assert result.state == ExecutorState.COMPLETED
    duration = perf_counter() - started

    assert duration < 2.0

