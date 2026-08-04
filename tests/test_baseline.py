from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from baseline.engine import BaselineEngine
from baseline.models import BaselineSnapshot, RegressionEvent
from baseline.schemas import BaselineCreate
from research.models import Research, ResearchScore
from trend.ports import TrendObservation

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False}, poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class FakeSource:
    def __init__(self, observations: list[TrendObservation]) -> None:
        self.observations = observations

    def history(self, entity_id: UUID) -> list[TrendObservation]:
        return self.observations


def _observations() -> list[TrendObservation]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        TrendObservation(1, start, 90, 80, 70, 60, 50, 40),
        TrendObservation(2, start + timedelta(days=1), 58, 54, 51, 45, 41, 35),
    ]


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


def test_engine_classifies_all_metrics_and_persists_events(db: Session) -> None:
    entity_id = uuid4()
    engine = BaselineEngine(db, FakeSource(_observations()))
    baseline = engine.set(entity_id, BaselineCreate(research_id=1))
    result = engine.evaluate(entity_id)

    assert baseline.algorithm_version == "1.0"
    assert {event.metric: event.severity for event in result.regressions} == {
        "visibility": "CRITICAL",
        "mention": "MAJOR",
        "recommendation": "MODERATE",
        "citation": "MODERATE",
        "coverage": "MINOR",
        "confidence": "MINOR",
    }
    assert db.scalar(select(func.count(RegressionEvent.id))) == 6


def test_latest_policy_updates_baseline_after_evaluation(db: Session) -> None:
    entity_id = uuid4()
    engine = BaselineEngine(db, FakeSource(_observations()))
    engine.set(
        entity_id,
        BaselineCreate(research_id=1, update_policy="LATEST"),
    )
    result = engine.evaluate(entity_id)
    stored = engine.get(entity_id)

    assert result.baseline_research_id == 1
    assert result.baseline_updated is True
    assert stored.research_id == 2
    assert [snapshot.reason for snapshot in stored.snapshots] == ["CREATED", "AUTO_LATEST"]
    assert db.scalar(select(func.count(BaselineSnapshot.id))) == 2


def _seed_scores(entity_id: UUID) -> None:
    start = datetime(2026, 2, 1, tzinfo=UTC)
    with TestingSession() as db:
        for index, value in enumerate((80.0, 50.0), start=1):
            research = Research(
                entity_id=entity_id,
                title=str(index),
                created_at=start + timedelta(days=index),
            )
            db.add(research)
            db.flush()
            db.add(ResearchScore(
                research_id=research.id, mention_score=value,
                recommendation_score=value, citation_score=value,
                coverage_score=value, confidence_score=value,
                visibility_score=value, version="1.0",
                calculated_at=start + timedelta(days=index),
            ))
        db.commit()


def test_baseline_api_and_openapi(client: TestClient) -> None:
    entity_id = uuid4()
    _seed_scores(entity_id)
    created = client.post(f"/entities/{entity_id}/baseline", json={"research_id": 1})
    fetched = client.get(f"/entities/{entity_id}/baseline")
    evaluated = client.post(f"/entities/{entity_id}/baseline/evaluate")

    assert created.status_code == 201
    assert fetched.status_code == 200
    assert evaluated.status_code == 200
    assert len(evaluated.json()["regressions"]) == 6
    paths = client.get("/openapi.json").json()["paths"]
    assert "/entities/{entity_id}/baseline" in paths
    assert "/entities/{entity_id}/baseline/evaluate" in paths


def test_baseline_api_errors_and_validation(client: TestClient) -> None:
    entity_id = uuid4()
    assert client.get(f"/entities/{entity_id}/baseline").status_code == 404
    assert client.post(f"/entities/{entity_id}/baseline", json={}).status_code == 404
    assert client.post(f"/entities/{entity_id}/baseline/evaluate").status_code == 404
    assert client.get("/entities/not-a-uuid/baseline").status_code == 422
