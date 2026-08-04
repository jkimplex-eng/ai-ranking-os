from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from scheduler.engine import SchedulerEngine, next_run_at
from scheduler.models import ScheduleExecution, ScheduleExecutionStatus, ScheduleType
from scheduler.ports import ResearchLaunchRequest, ResearchLaunchResult
from scheduler.schemas import ScheduleCreate

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)
NOW = datetime(2026, 1, 31, 12, 0, tzinfo=UTC)


class FakeLauncher:
    def __init__(self, failures: int = 0) -> None:
        self.failures = failures
        self.calls = 0

    def launch(self, request: ResearchLaunchRequest) -> ResearchLaunchResult:
        self.calls += 1
        if self.calls <= self.failures:
            return ResearchLaunchResult(self.calls, False, "temporary failure")
        return ResearchLaunchResult(100 + self.calls, True)


@pytest.fixture
def db() -> Generator[Session]:
    Base.metadata.create_all(test_engine)
    with TestingSession() as session:
        yield session
    Base.metadata.drop_all(test_engine)


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


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        (ScheduleType.HOURLY, datetime(2026, 1, 31, 13, 0, tzinfo=UTC)),
        (ScheduleType.DAILY, datetime(2026, 2, 1, 12, 0, tzinfo=UTC)),
        (ScheduleType.WEEKLY, datetime(2026, 2, 7, 12, 0, tzinfo=UTC)),
        (ScheduleType.MONTHLY, datetime(2026, 2, 28, 12, 0, tzinfo=UTC)),
    ],
)
def test_next_run_for_standard_schedules(kind: ScheduleType, expected: datetime) -> None:
    assert next_run_at(kind, NOW) == expected


def test_next_run_supports_standard_cron_expression() -> None:
    assert next_run_at(ScheduleType.CRON, NOW, "*/15 9-17 * * 1-5") == datetime(
        2026, 2, 2, 9, 0, tzinfo=UTC
    )


def _payload(**overrides: object) -> ScheduleCreate:
    values = {
        "name": "Daily visibility",
        "research_id": 7,
        "schedule_type": "DAILY",
        "models": [{"provider": "test", "model": "model-a"}],
        "start_at": NOW,
        "retry_policy": {"max_attempts": 3, "base_delay_seconds": 1},
    }
    values.update(overrides)
    return ScheduleCreate.model_validate(values)


def test_run_due_retries_and_preserves_full_history(db: Session) -> None:
    launcher = FakeLauncher(failures=2)
    delays: list[float] = []
    engine = SchedulerEngine(db, launcher, clock=lambda: NOW, sleeper=delays.append)
    engine.create(_payload())

    executions = engine.run_due()

    assert len(executions) == 1
    execution = executions[0]
    assert execution.status == "COMPLETED"
    assert execution.attempts == 3
    assert [item.status for item in execution.history] == ["FAILED", "FAILED", "COMPLETED"]
    assert [item.retry_delay_seconds for item in execution.history] == [0, 1, 2]
    assert delays == [1, 2]
    schedule = engine.list()[0]
    assert schedule.last_run_at == NOW
    assert schedule.next_run_at == datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


def test_run_due_skips_schedule_with_active_execution(db: Session) -> None:
    engine = SchedulerEngine(db, FakeLauncher(), clock=lambda: NOW, sleeper=lambda _: None)
    schedule = engine.create(_payload())
    db.add(
        ScheduleExecution(
            schedule_id=schedule.id,
            status=ScheduleExecutionStatus.RUNNING,
            attempts=0,
            scheduled_for=NOW,
            started_at=NOW,
        )
    )
    db.commit()

    assert engine.run_due() == []
    assert len(db.scalars(select(ScheduleExecution)).all()) == 1


def test_schedule_api_crud_run_validation_and_openapi(client: TestClient) -> None:
    created = client.post(
        "/schedules",
        json={
            "name": "Weekly research",
            "research_id": 1,
            "schedule_type": "WEEKLY",
            "models": [{"provider": "test", "model": "model-a"}],
            "is_enabled": False,
        },
    )
    assert created.status_code == 201
    schedule_id = created.json()["id"]
    assert client.get("/schedules").json()[0]["name"] == "Weekly research"
    updated = client.patch(f"/schedules/{schedule_id}", json={"is_enabled": True})
    assert updated.status_code == 200
    assert updated.json()["is_enabled"] is True
    assert client.post("/schedules/run").status_code == 200
    assert client.delete(f"/schedules/{schedule_id}").status_code == 204
    assert client.patch("/schedules/999", json={"is_enabled": False}).status_code == 404
    invalid = client.post(
        "/schedules",
        json={
            "name": "Broken cron",
            "research_id": 1,
            "schedule_type": "CRON",
            "cron_expression": "broken",
            "models": [{"provider": "test", "model": "x"}],
        },
    )
    assert invalid.status_code == 422
    paths = client.get("/openapi.json").json()["paths"]
    assert "/schedules" in paths
    assert "/schedules/{schedule_id}" in paths
    assert "/schedules/run" in paths

