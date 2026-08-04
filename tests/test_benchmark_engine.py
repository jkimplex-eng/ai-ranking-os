from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from analytics.ports import AnalyticsRecord
from backend.app.database import Base, get_db
from backend.app.main import app
from benchmark.models import BenchmarkEntry, BenchmarkRun
from benchmark.repository import SqlAlchemyBenchmarkRepository
from benchmark.schemas import SUPPORTED_METRICS, BenchmarkRequest
from benchmark.service import BenchmarkDataUnavailableError, BenchmarkService
from research.models import Research, ResearchScore, ResearchStatus

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class FakeSource:
    def records(self, date_from=None, date_to=None) -> list[AnalyticsRecord]:
        def metrics(value: float) -> dict[str, float]:
            return {metric: value for metric in SUPPORTED_METRICS}

        return [
            AnalyticsRecord(datetime(2026, 1, 1, tzinfo=UTC), {"entity_id": "a"}, metrics(80)),
            AnalyticsRecord(datetime(2026, 1, 2, tzinfo=UTC), {"entity_id": "a"}, metrics(100)),
            AnalyticsRecord(datetime(2026, 1, 1, tzinfo=UTC), {"entity_id": "b"}, metrics(60)),
            AnalyticsRecord(datetime(2026, 1, 1, tzinfo=UTC), {"entity_id": "c"}, metrics(60)),
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


def test_benchmark_ranking_percentiles_and_comparative_analysis(db: Session) -> None:
    service = BenchmarkService(FakeSource(), SqlAlchemyBenchmarkRepository(db))
    result = service.execute(BenchmarkRequest(metrics=["visibility", "mention"]))

    leader, tied_b, tied_c = result.entries
    assert leader.entity_id == "a"
    assert leader.observation_count == 2
    assert leader.overall_score == 90
    assert leader.overall_rank == 1
    assert leader.overall_percentile == 100
    visibility = leader.metrics["visibility"]
    assert visibility.population_average == 70
    assert visibility.delta_from_average == 20
    assert visibility.delta_from_leader == 0
    assert tied_b.overall_rank == tied_c.overall_rank == 2
    assert tied_b.overall_percentile == 50


def test_benchmark_filters_entities_persists_and_restores(db: Session) -> None:
    service = BenchmarkService(FakeSource(), SqlAlchemyBenchmarkRepository(db))
    result = service.execute(BenchmarkRequest(entity_ids=["b"], metrics=["coverage"]))
    restored = service.get(result.id)

    assert restored == result
    assert result.entity_count == 1
    assert result.entries[0].overall_percentile == 100
    assert service.list(1, 1).total == 1
    assert db.scalar(select(func.count(BenchmarkRun.id))) == 1
    assert db.scalar(select(func.count(BenchmarkEntry.id))) == 1
    with pytest.raises(BenchmarkDataUnavailableError):
        service.execute(BenchmarkRequest(entity_ids=["missing"]))


def _seed_score(entity_id, value: float) -> None:
    with TestingSession() as db:
        research = Research(
            entity_id=entity_id,
            title=str(entity_id),
            status=ResearchStatus.COMPLETED,
            metadata_payload={},
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
                version="1.0",
            )
        )
        db.commit()


def test_benchmark_api_create_list_get_and_openapi(client: TestClient) -> None:
    first, second = uuid4(), uuid4()
    _seed_score(first, 85)
    _seed_score(second, 55)
    created = client.post("/benchmarks", json={})
    benchmark_id = created.json()["id"]

    assert created.status_code == 201
    assert created.json()["entity_count"] == 2
    assert created.json()["entries"][0]["entity_id"] == str(first)
    assert client.get(f"/benchmarks/{benchmark_id}").status_code == 200
    assert client.get("/benchmarks").json()["total"] == 1
    paths = client.get("/openapi.json").json()["paths"]
    assert "/benchmarks" in paths
    assert "/benchmarks/{id}" in paths


def test_benchmark_api_validation_and_errors(client: TestClient) -> None:
    assert client.post("/benchmarks", json={}).status_code == 422
    _seed_score(uuid4(), 50)
    assert client.post("/benchmarks", json={"metrics": ["unknown"]}).status_code == 422
    assert client.post("/benchmarks", json={"entity_ids": ["missing"]}).status_code == 422
    assert client.get("/benchmarks/999").status_code == 404
    assert client.get("/benchmarks", params={"page_size": 101}).status_code == 422
