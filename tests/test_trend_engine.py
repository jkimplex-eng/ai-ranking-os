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
from research.models import Research, ResearchScore
from trend.engine import TrendEngine
from trend.models import TrendPoint, TrendSeries, TrendSnapshot
from trend.ports import TrendObservation

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class FakeTrendSource:
    def __init__(self, observations: list[TrendObservation]) -> None:
        self.observations = observations

    def history(self, entity_id: UUID) -> list[TrendObservation]:
        return self.observations


def _observations() -> list[TrendObservation]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        TrendObservation(1, start, 40, 60, 50, 30, 45, 80),
        TrendObservation(2, start + timedelta(days=1), 50, 60.5, 40, 30, 55, 80),
        TrendObservation(3, start + timedelta(days=2), 70, 40, 41, 60, 65, 82),
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


def test_engine_calculates_metrics_and_persists_snapshots(db: Session) -> None:
    entity_id = uuid4()
    engine = TrendEngine(db, FakeTrendSource(_observations()))

    first = engine.build(entity_id)
    second = engine.build(entity_id)

    visibility = next(item for item in first.metrics if item.metric == "visibility")
    mention = next(item for item in first.metrics if item.metric == "mention")
    assert [point.moving_average for point in visibility.points] == [40, 45, 53.33]
    assert [point.percentage_change for point in visibility.points] == [None, 25, 40]
    assert [point.direction for point in visibility.points] == ["STABLE", "UP", "UP"]
    assert [point.direction for point in mention.points] == ["STABLE", "STABLE", "DOWN"]
    assert second.series_id == first.series_id
    assert second.snapshot_id != first.snapshot_id
    assert db.scalar(select(func.count(TrendSeries.id))) == 1
    assert db.scalar(select(func.count(TrendSnapshot.id))) == 2
    assert db.scalar(select(func.count(TrendPoint.id))) == 36


def _seed_scored_research(entity_id: UUID) -> None:
    start = datetime(2026, 2, 1, tzinfo=UTC)
    with TestingSession() as db:
        for index, value in enumerate((25.0, 50.0, 75.0), start=1):
            research = Research(
                entity_id=entity_id,
                title=f"Trend {index}",
                created_at=start + timedelta(days=index),
            )
            db.add(research)
            db.flush()
            db.add(
                ResearchScore(
                    research_id=research.id,
                    mention_score=value,
                    recommendation_score=value - 1,
                    citation_score=value - 2,
                    coverage_score=value - 3,
                    confidence_score=value + 1,
                    visibility_score=value,
                    calculated_at=start + timedelta(days=index),
                    version="1.0",
                )
            )
        db.commit()


def test_trend_api_all_metrics_metric_filter_and_openapi(client: TestClient) -> None:
    entity_id = uuid4()
    _seed_scored_research(entity_id)

    complete = client.get(f"/entities/{entity_id}/trend")
    metric = client.get(f"/entities/{entity_id}/trend/visibility")

    assert complete.status_code == 200
    assert {item["metric"] for item in complete.json()["metrics"]} == {
        "visibility", "mention", "recommendation", "citation", "coverage", "confidence"
    }
    assert metric.status_code == 200
    assert metric.json()["metric"] == "visibility"
    assert len(metric.json()["points"]) == 3
    paths = client.get("/openapi.json").json()["paths"]
    assert "/entities/{entity_id}/trend" in paths
    assert "/entities/{entity_id}/trend/{metric}" in paths


def test_trend_api_validation_and_missing_data(client: TestClient) -> None:
    entity_id = uuid4()
    assert client.get(f"/entities/{entity_id}/trend").status_code == 404
    assert client.get(f"/entities/{entity_id}/trend/not-a-metric").status_code == 422
    assert client.get("/entities/not-a-uuid/trend").status_code == 422

