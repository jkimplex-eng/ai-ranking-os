from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from decision_center.models import AgentType, Task, TaskStatus
from execution_engine import service
from execution_engine.models import Execution, ExecutionState
from execution_engine.worker_manager import WorkerManager

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


def create_agent(
    client: TestClient,
    *,
    name: str,
    agent_type: str = "CODEX",
    specialization: str | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/agents",
        json={
            "name": name,
            "agent_type": agent_type,
            "specialization": specialization,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_ready_task(
    client: TestClient,
    *,
    title: str,
    priority: str = "MEDIUM",
    specialization: str | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/tasks",
        json={
            "title": title,
            "status": "READY",
            "priority": priority,
            "required_specialization": specialization,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_priority_queue_and_full_execution_lifecycle(client: TestClient) -> None:
    agent = create_agent(client, name="General Codex")
    low = create_ready_task(client, title="Low task", priority="LOW")
    high = create_ready_task(client, title="High task", priority="HIGH")
    medium = create_ready_task(client, title="Medium task", priority="MEDIUM")

    queue = client.get("/queue")
    assert queue.status_code == 200
    assert [task["id"] for task in queue.json()] == [high["id"], medium["id"], low["id"]]

    response = client.post("/execution/start")
    assert response.status_code == 201
    execution = response.json()
    assert execution["task_id"] == high["id"]
    assert execution["agent_id"] == agent["id"]
    assert execution["state"] == "COMPLETED"
    assert execution["attempt_count"] == 1
    assert execution["started_at"] is not None
    assert execution["finished_at"] is not None
    assert execution["duration_ms"] is not None
    assert execution["result"]["agent_type"] == "CODEX"
    assert execution["error"] is None

    task_response = client.get(f"/tasks/{high['id']}")
    assert task_response.json()["status"] == "DONE"
    assert client.get(f"/execution/{execution['id']}").status_code == 200
    assert client.get("/execution/history").json()[0]["id"] == execution["id"]


def test_scheduler_matches_specialization_and_skips_reserved_agents(
    client: TestClient,
) -> None:
    create_agent(
        client,
        name="Reserved Claude",
        agent_type="CLAUDE",
        specialization="backend",
    )
    frontend = create_agent(
        client,
        name="Frontend Qwen",
        agent_type="QWEN",
        specialization="frontend",
    )
    backend = create_agent(
        client,
        name="Backend DeepSeek",
        agent_type="DEEPSEEK",
        specialization="backend",
    )
    task = create_ready_task(
        client,
        title="Backend task",
        priority="HIGH",
        specialization="backend",
    )

    response = client.post("/execution/start")
    assert response.status_code == 201
    assert response.json()["task_id"] == task["id"]
    assert response.json()["agent_id"] == backend["id"]
    assert response.json()["agent_id"] != frontend["id"]


def test_retry_uses_exponential_backoff_and_eventually_completes(
    client: TestClient,
) -> None:
    agent = create_agent(client, name="Retry Codex")
    task_data = create_ready_task(client, title="Flaky task")
    attempts = 0
    delays: list[float] = []

    def flaky_executor(task: Task) -> dict[str, Any]:
        nonlocal attempts
        attempts += 1
        if attempts < 4:
            raise RuntimeError(f"temporary failure {attempts}")
        return {"task_id": task.id, "recovered": True}

    manager = WorkerManager({AgentType.CODEX: flaky_executor})
    with TestingSession() as session:
        execution = service.start_next_execution(
            session,
            manager,
            retry_base_seconds=1,
            sleep=delays.append,
        )

    assert execution.task_id == task_data["id"]
    assert execution.agent_id == agent["id"]
    assert execution.state == ExecutionState.COMPLETED
    assert execution.attempt_count == 4
    assert execution.result == {"task_id": task_data["id"], "recovered": True}
    assert delays == [1, 2, 4]


def test_execution_fails_after_three_retries(client: TestClient) -> None:
    create_agent(client, name="Failing Codex")
    task_data = create_ready_task(client, title="Always failing")

    def failing_executor(task: Task) -> dict[str, Any]:
        raise RuntimeError(f"cannot execute task {task.id}")

    manager = WorkerManager({AgentType.CODEX: failing_executor})
    with TestingSession() as session:
        execution = service.start_next_execution(
            session,
            manager,
            retry_base_seconds=0,
            sleep=lambda _: None,
        )
        task = session.get(Task, task_data["id"])

    assert execution.state == ExecutionState.FAILED
    assert execution.attempt_count == 4
    assert execution.error == f"cannot execute task {task_data['id']}"
    assert task is not None
    assert task.status == TaskStatus.BLOCKED


def test_scheduler_does_not_assign_two_active_tasks_to_one_agent(
    client: TestClient,
) -> None:
    create_agent(client, name="Only Agent")
    first = create_ready_task(client, title="First", priority="HIGH")
    create_ready_task(client, title="Second", priority="LOW")
    manager = WorkerManager()

    with TestingSession() as session:
        execution, task, _ = service.schedule_execution(session, manager)
        assert task.id == first["id"]
        assert execution.state == ExecutionState.ASSIGNED

    with TestingSession() as session, pytest.raises(service.NoAgentAvailableError):
        service.schedule_execution(session, manager)


def test_scheduler_recovers_execution_left_running_by_interrupted_worker(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_agent(client, name="Recoverable Agent")
    stale_task = create_ready_task(client, title="Interrupted", priority="HIGH")
    next_task = create_ready_task(client, title="Next", priority="LOW")

    with TestingSession() as session:
        stale_execution, task, _ = service.schedule_execution(session, WorkerManager())
        stale_execution.state = ExecutionState.RUNNING
        stale_execution.started_at = datetime.now(UTC) - timedelta(minutes=30)
        session.commit()
        stale_execution_id = stale_execution.id
        assert task.id == stale_task["id"]

    monkeypatch.setenv("EXECUTION_STALE_SECONDS", "900")
    with TestingSession() as session:
        execution, task, _ = service.schedule_execution(session, WorkerManager())
        recovered = session.get(Execution, stale_execution_id)
        interrupted = session.get(Task, stale_task["id"])

    assert recovered is not None
    assert recovered.state == ExecutionState.FAILED
    assert recovered.error == "Execution expired after worker interruption"
    assert interrupted is not None
    assert interrupted.status == TaskStatus.BLOCKED
    assert interrupted.owner_id is None
    assert task.id == next_task["id"]
    assert execution.state == ExecutionState.ASSIGNED


def test_cancel_requeues_an_active_execution(client: TestClient) -> None:
    create_agent(client, name="Cancellable Agent")
    task_data = create_ready_task(client, title="Cancel me")
    with TestingSession() as session:
        execution, _, _ = service.schedule_execution(session, WorkerManager())
        execution_id = execution.id

    response = client.post("/execution/cancel", json={"execution_id": execution_id})
    assert response.status_code == 200
    assert response.json()["state"] == "CANCELLED"
    task_response = client.get(f"/tasks/{task_data['id']}")
    assert task_response.json()["status"] == "READY"
    assert task_response.json()["owner_id"] is None
