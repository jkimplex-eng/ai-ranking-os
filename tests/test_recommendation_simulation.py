from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from recommendation.engine import RecommendationEngine
from recommendation.models import RecommendationPriority, RecommendationRule
from recommendation.ports import ResearchScoreSnapshot
from recommendation.simulation.models import RecommendationSimulation
from recommendation.simulation.simulator import ImpactSimulator
from recommendation.templates.models import RecommendationTemplate

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)

DEFINITIONS = (
    (
        "mention",
        "MENTION_GROWTH",
        "mention_score",
        60.0,
        RecommendationPriority.HIGH,
    ),
    (
        "citation",
        "CITATION_AUTHORITY",
        "citation_score",
        50.0,
        RecommendationPriority.HIGH,
    ),
    (
        "trust",
        "TRUST_SIGNALS",
        "recommendation_score",
        60.0,
        RecommendationPriority.CRITICAL,
    ),
    (
        "coverage",
        "SOURCE_EXPANSION",
        "coverage_score",
        70.0,
        RecommendationPriority.MEDIUM,
    ),
)


class FakeScoreSource:
    def __init__(self, snapshot: ResearchScoreSnapshot) -> None:
        self.snapshot = snapshot

    def get_latest(self, research_id: int) -> ResearchScoreSnapshot:
        assert research_id == self.snapshot.research_id
        return self.snapshot


def _snapshot(research_id: int = 7) -> ResearchScoreSnapshot:
    return ResearchScoreSnapshot(
        research_id=research_id,
        version="1.0",
        mention_score=20,
        recommendation_score=20,
        citation_score=20,
        coverage_score=20,
        confidence_score=80,
        visibility_score=40,
    )


def _seed(db: Session) -> None:
    for code, recommendation_type, metric, threshold, priority in DEFINITIONS:
        db.add(
            RecommendationTemplate(
                template_code=f"{code}-plan",
                recommendation_type=recommendation_type,
                title=f"{recommendation_type} plan",
                description="Deterministic action plan.",
                steps=["Audit.", "Execute.", "Measure."],
                expected_result=f"Improve {metric}.",
                estimated_time="2-4 weeks",
                priority=priority,
                version="1.0",
            )
        )
        db.add(
            RecommendationRule(
                code=f"v1-{code}",
                recommendation_type=recommendation_type,
                metric=metric,
                operator="lt",
                threshold=threshold,
                priority=priority,
                explanation_template=(
                    "{metric} is {metric_value}, below {threshold}."
                ),
                expected_effect=f"Increase {metric}.",
                version="1.0",
                is_active=True,
            )
        )
    db.commit()


@pytest.fixture
def db() -> Generator[Session]:
    Base.metadata.create_all(test_engine)
    with TestingSession() as session:
        _seed(session)
        yield session
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def client() -> Generator[TestClient]:
    Base.metadata.create_all(test_engine)
    with TestingSession() as session:
        _seed(session)

    def override_get_db() -> Generator[Session]:
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)


def test_simulator_uses_deterministic_scoring_v1_weights(db: Session) -> None:
    source = FakeScoreSource(_snapshot())
    RecommendationEngine(db, source).generate(7)

    result = ImpactSimulator(db, source).simulate(7)

    assert result.model_version == "1.0"
    assert len(result.simulations) == 4
    by_metric = {item.metric: item for item in result.simulations}
    mention = by_metric["mention_score"]
    assert mention.current_metric == 20
    assert mention.expected_metric_change == 30
    assert mention.current_visibility == 40
    assert mention.predicted_visibility == 50.5
    assert mention.predicted_delta == 10.5
    assert mention.confidence_min == 47.0
    assert mention.confidence_expected == 50.5
    assert mention.confidence_max == 54.0
    assert mention.estimated_duration_days == 21
    assert db.scalar(select(func.count(RecommendationSimulation.id))) == 4


def test_simulation_is_reproducible_and_latest_is_persisted(db: Session) -> None:
    source = FakeScoreSource(_snapshot())
    RecommendationEngine(db, source).generate(7)
    simulator = ImpactSimulator(db, source)

    first = simulator.simulate(7)
    second = simulator.simulate(7)
    latest = simulator.get_latest(7)

    first_values = [
        (item.metric, item.predicted_visibility) for item in first.simulations
    ]
    second_values = [
        (item.metric, item.predicted_visibility) for item in second.simulations
    ]
    assert first_values == second_values
    assert [item.id for item in latest.simulations] == [
        item.id for item in second.simulations
    ]


def _create_research_flow(client: TestClient) -> int:
    research = client.post(
        "/research",
        json={"title": "Acme", "metadata": {"target_entity": "Acme"}},
    )
    research_id = research.json()["id"]
    task = client.post(
        "/research-tasks",
        json={
            "research_id": research_id,
            "query": "Acme",
            "provider": "test",
            "model": "model-a",
        },
    )
    client.post(
        "/responses",
        json={
            "research_task_id": task.json()["id"],
            "provider": "test",
            "model": "model-a",
            "content": "Acme is present.",
        },
    )
    assert client.post(f"/research/{research_id}/score").status_code == 200
    assert client.post(
        f"/research/{research_id}/recommendations"
    ).status_code == 201
    return research_id


def test_simulation_api_persists_and_returns_full_forecast(
    client: TestClient,
) -> None:
    research_id = _create_research_flow(client)

    created = client.post(f"/research/{research_id}/simulate")
    fetched = client.get(f"/research/{research_id}/simulation")

    assert created.status_code == 201
    assert fetched.status_code == 200
    assert fetched.json() == created.json()
    assert created.json()["simulations"]
    for item in created.json()["simulations"]:
        assert item["confidence_min"] <= item["confidence_expected"]
        assert item["confidence_expected"] <= item["confidence_max"]
        assert item["predicted_visibility"] == item["confidence_expected"]
        assert item["estimated_duration_days"] == 21


def test_simulation_api_errors_and_openapi(client: TestClient) -> None:
    research = client.post("/research", json={"title": "No score"}).json()

    assert client.post(
        f"/research/{research['id']}/simulate"
    ).status_code == 409
    assert client.get(
        f"/research/{research['id']}/simulation"
    ).status_code == 404
    assert client.post("/research/999999/simulate").status_code == 404
    paths = client.get("/openapi.json").json()["paths"]
    assert "/research/{research_id}/simulate" in paths
    assert "/research/{research_id}/simulation" in paths
