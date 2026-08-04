from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from analytics.models import AnalyticsRun
from analytics.ports import AnalyticsRecord
from analytics.repository import SqlAlchemyAnalyticsRepository
from analytics.schemas import (
    AnalyticsFilter,
    AnalyticsQuery,
    FilterOperator,
    Statistic,
    TimeInterval,
)
from analytics.service import AnalyticsService
from backend.app.database import Base, get_db
from backend.app.main import app
from research.models import Research, ResearchScore, ResearchStatus

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class FakeAnalyticsDataSource:
    def records(self, date_from=None, date_to=None) -> list[AnalyticsRecord]:
        records = [
            AnalyticsRecord(
                datetime(2026, 1, 1, 10, tzinfo=UTC),
                {"status": "COMPLETED", "entity_id": "one"},
                {"visibility": 60, "mention": 50},
            ),
            AnalyticsRecord(
                datetime(2026, 1, 1, 18, tzinfo=UTC),
                {"status": "COMPLETED", "entity_id": "two"},
                {"visibility": 80, "mention": 70},
            ),
            AnalyticsRecord(
                datetime(2026, 1, 2, 9, tzinfo=UTC),
                {"status": "FAILED", "entity_id": "three"},
                {"visibility": 20, "mention": 10},
            ),
        ]
        return [
            item
            for item in records
            if (date_from is None or item.observed_at >= date_from)
            and (date_to is None or item.observed_at <= date_to)
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


def test_service_filters_groups_intervals_and_calculates_statistics(db: Session) -> None:
    service = AnalyticsService(FakeAnalyticsDataSource(), SqlAlchemyAnalyticsRepository(db))
    query = AnalyticsQuery(
        metrics=["visibility"],
        group_by=["status"],
        filters=[AnalyticsFilter(field="visibility", operator=FilterOperator.GTE, value=50)],
        interval=TimeInterval.DAY,
        statistics=list(Statistic),
    )
    result = service.execute(query)
    values = result.groups[0].metrics["visibility"].values

    assert result.engine_version == "1.0"
    assert result.source_record_count == 2
    assert result.group_count == 1
    assert result.groups[0].dimensions == {"status": "COMPLETED"}
    assert result.groups[0].interval_start == datetime(2026, 1, 1, tzinfo=UTC)
    assert values[Statistic.COUNT] == 2
    assert values[Statistic.SUM] == 140
    assert values[Statistic.AVG] == 70
    assert values[Statistic.MEDIAN] == 70
    assert values[Statistic.STDDEV] == 10
    assert values[Statistic.P95] == 79


def test_repository_history_is_reproducible_and_paginated(db: Session) -> None:
    service = AnalyticsService(FakeAnalyticsDataSource(), SqlAlchemyAnalyticsRepository(db))
    first = service.execute(AnalyticsQuery(metrics=["visibility"]))
    second = service.execute(AnalyticsQuery(metrics=["mention"]))

    restored = service.get(first.run_id)
    page = service.list(page=1, page_size=1)
    assert restored == first
    assert page.total == 2
    assert page.items[0].id == second.run_id
    assert db.scalar(select(func.count(AnalyticsRun.id))) == 2


def _seed_platform_score() -> int:
    with TestingSession() as db:
        research = Research(
            entity_id=uuid4(),
            title="Analytics source",
            status=ResearchStatus.COMPLETED,
            metadata_payload={},
        )
        db.add(research)
        db.flush()
        db.add(
            ResearchScore(
                research_id=research.id,
                mention_score=65,
                recommendation_score=70,
                citation_score=55,
                coverage_score=80,
                confidence_score=90,
                visibility_score=72,
                version="1.0",
            )
        )
        db.commit()
        return research.id


def test_analytics_api_executes_lists_gets_and_updates_openapi(client: TestClient) -> None:
    research_id = _seed_platform_score()
    response = client.post(
        "/analytics/query",
        json={
            "metrics": ["visibility", "mention"],
            "group_by": ["status"],
            "filters": [{"field": "research_id", "operator": "EQ", "value": str(research_id)}],
            "statistics": ["COUNT", "AVG", "MAX"],
        },
    )
    run_id = response.json()["run_id"]

    assert response.status_code == 201
    assert response.json()["source_record_count"] == 1
    assert response.json()["groups"][0]["metrics"]["visibility"]["values"]["AVG"] == 72
    assert client.get(f"/analytics/runs/{run_id}").status_code == 200
    listing = client.get("/analytics/runs", params={"page": 1, "page_size": 10})
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    paths = client.get("/openapi.json").json()["paths"]
    assert "/analytics/query" in paths
    assert "/analytics/runs" in paths
    assert "/analytics/runs/{id}" in paths


def test_analytics_api_validation_and_errors(client: TestClient) -> None:
    _seed_platform_score()
    assert client.post("/analytics/query", json={"metrics": []}).status_code == 422
    assert client.post("/analytics/query", json={"metrics": ["unknown"]}).status_code == 422
    assert client.get("/analytics/runs/999").status_code == 404
    assert client.get("/analytics/runs", params={"page_size": 101}).status_code == 422
