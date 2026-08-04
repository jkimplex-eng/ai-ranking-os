from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from analytics.ports import AnalyticsRecord
from backend.app.database import Base, get_db
from backend.app.main import app
from insights.models import Insight, InsightRun
from insights.repository import SqlAlchemyInsightRepository
from insights.schemas import InsightRequest, InsightType
from insights.service import InsightDataUnavailableError, InsightService
from research.models import Research, ResearchScore, ResearchStatus

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class FakeSource:
    def records(self, date_from=None, date_to=None) -> list[AnalyticsRecord]:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        return [
            AnalyticsRecord(start, {"entity_id": "a"}, {"visibility": 50}),
            AnalyticsRecord(start + timedelta(days=1), {"entity_id": "a"}, {"visibility": 52}),
            AnalyticsRecord(start + timedelta(days=2), {"entity_id": "a"}, {"visibility": 90}),
            AnalyticsRecord(start, {"entity_id": "b"}, {"visibility": 80}),
            AnalyticsRecord(start + timedelta(days=1), {"entity_id": "b"}, {"visibility": 70}),
            AnalyticsRecord(start + timedelta(days=2), {"entity_id": "b"}, {"visibility": 40}),
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


def test_engine_detects_growth_decline_anomalies_leaders_changes_and_recommendations(
    db: Session,
) -> None:
    service = InsightService(FakeSource(), SqlAlchemyInsightRepository(db))
    result = service.generate(
        InsightRequest(metrics=["visibility"], change_threshold=5, anomaly_z_threshold=2)
    )
    types = {insight.insight_type for insight in result.insights}

    assert types == set(InsightType)
    assert result.source_record_count == 6
    assert result.insight_count == len(result.insights)
    leader = next(
        item
        for item in result.insights
        if item.insight_type is InsightType.LEADER and item.evidence["rank"] == 1
    )
    decline = next(item for item in result.insights if item.insight_type is InsightType.DECLINE)
    anomaly = next(
        item
        for item in result.insights
        if item.insight_type is InsightType.ANOMALY and item.entity_id == "b"
    )
    assert leader.entity_id == "a"
    assert decline.percentage_change == -50
    assert decline.recommendation is not None
    assert anomaly.evidence["z_score"] == -7


def test_insight_snapshot_restores_filters_and_paginates(db: Session) -> None:
    service = InsightService(FakeSource(), SqlAlchemyInsightRepository(db))
    result = service.generate(InsightRequest(entity_ids=["a"], metrics=["visibility"]))

    assert service.get(result.id) == result
    assert result.source_record_count == 3
    assert service.list(1, 1).total == 1
    assert db.scalar(select(func.count(InsightRun.id))) == 1
    assert db.scalar(select(func.count(Insight.id))) == result.insight_count
    with pytest.raises(InsightDataUnavailableError):
        service.generate(InsightRequest(entity_ids=["missing"]))


def _seed_history(entity_id, values: list[float]) -> None:
    with TestingSession() as db:
        for index, value in enumerate(values):
            research = Research(
                entity_id=entity_id,
                title=f"{entity_id}-{index}",
                status=ResearchStatus.COMPLETED,
                metadata_payload={},
                created_at=datetime(2026, 1, index + 1, tzinfo=UTC),
            )
            db.add(research)
            db.flush()
            db.add(
                ResearchScore(
                    research_id=research.id,
                    mention_score=value,
                    recommendation_score=value,
                    citation_score=value,
                    coverage_score=value,
                    confidence_score=value,
                    visibility_score=value,
                    calculated_at=datetime(2026, 1, index + 1, tzinfo=UTC),
                    version="1.0",
                )
            )
        db.commit()


def test_insights_api_generate_list_get_and_openapi(client: TestClient) -> None:
    entity = uuid4()
    _seed_history(entity, [50, 55, 80])
    created = client.post(
        "/insights/generate",
        json={"entity_ids": [str(entity)], "metrics": ["visibility"]},
    )
    run_id = created.json()["id"]

    assert created.status_code == 201
    assert created.json()["source_record_count"] == 3
    assert any(item["insight_type"] == "GROWTH" for item in created.json()["insights"])
    assert client.get(f"/insights/runs/{run_id}").status_code == 200
    assert client.get("/insights/runs").json()["total"] == 1
    paths = client.get("/openapi.json").json()["paths"]
    assert "/insights/generate" in paths
    assert "/insights/runs" in paths
    assert "/insights/runs/{id}" in paths


def test_insights_api_validation_and_errors(client: TestClient) -> None:
    assert client.post("/insights/generate", json={}).status_code == 422
    _seed_history(uuid4(), [50])
    assert client.post("/insights/generate", json={"metrics": ["unknown"]}).status_code == 422
    assert client.post("/insights/generate", json={"entity_ids": ["missing"]}).status_code == 422
    assert client.get("/insights/runs/999").status_code == 404
