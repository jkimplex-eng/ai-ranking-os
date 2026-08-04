from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from recommendation.engine import RecommendationEngine
from recommendation.models import (
    Recommendation,
    RecommendationExecution,
    RecommendationPriority,
    RecommendationRule,
)
from recommendation.ports import ResearchScoreSnapshot

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


class FakeScoreSource:
    def __init__(self, snapshot: ResearchScoreSnapshot) -> None:
        self.snapshot = snapshot

    def get_latest(self, research_id: int) -> ResearchScoreSnapshot:
        assert research_id == self.snapshot.research_id
        return self.snapshot


def _seed_rules(db: Session) -> None:
    rules = [
        (
            "mention",
            "MENTION_GROWTH",
            "mention_score",
            60,
            RecommendationPriority.HIGH,
        ),
        (
            "citation",
            "CITATION_AUTHORITY",
            "citation_score",
            50,
            RecommendationPriority.HIGH,
        ),
        (
            "recommendation",
            "TRUST_SIGNALS",
            "recommendation_score",
            60,
            RecommendationPriority.CRITICAL,
        ),
        (
            "coverage",
            "SOURCE_EXPANSION",
            "coverage_score",
            70,
            RecommendationPriority.MEDIUM,
        ),
    ]
    db.add_all(
        [
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
            for (
                code,
                recommendation_type,
                metric,
                threshold,
                priority,
            ) in rules
        ]
    )
    db.commit()


@pytest.fixture
def db() -> Generator[Session]:
    Base.metadata.create_all(test_engine)
    with TestingSession() as session:
        _seed_rules(session)
        yield session
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def client() -> Generator[TestClient]:
    Base.metadata.create_all(test_engine)
    with TestingSession() as session:
        _seed_rules(session)

    def override_get_db() -> Generator[Session]:
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)


def _snapshot(research_id: int = 7, value: float = 20) -> ResearchScoreSnapshot:
    return ResearchScoreSnapshot(
        research_id=research_id,
        version="1.0",
        mention_score=value,
        recommendation_score=value,
        citation_score=value,
        coverage_score=value,
        confidence_score=80,
        visibility_score=40,
    )


def test_rule_engine_generates_and_persists_actions(db: Session) -> None:
    result = RecommendationEngine(db, FakeScoreSource(_snapshot())).generate(7)

    assert result.status == "COMPLETED"
    assert result.engine_version == "1.0"
    assert result.score_version == "1.0"
    assert [item.recommendation_type for item in result.recommendations] == [
        "TRUST_SIGNALS",
        "MENTION_GROWTH",
        "CITATION_AUTHORITY",
        "SOURCE_EXPANSION",
    ]
    assert all(item.explanation for item in result.recommendations)
    assert all(item.expected_effect for item in result.recommendations)
    assert db.scalar(select(func.count(Recommendation.id))) == 4
    assert db.scalar(select(func.count(RecommendationExecution.id))) == 1


def test_rule_engine_can_return_an_empty_completed_set(db: Session) -> None:
    result = RecommendationEngine(
        db,
        FakeScoreSource(_snapshot(value=100)),
    ).generate(7)

    assert result.status == "COMPLETED"
    assert result.recommendations == []


def _create_scored_research(client: TestClient) -> int:
    research = client.post(
        "/research",
        json={"title": "Acme", "metadata": {"target_entity": "Acme"}},
    )
    assert research.status_code == 201
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
    assert task.status_code == 201
    response = client.post(
        "/responses",
        json={
            "research_task_id": task.json()["id"],
            "provider": "test",
            "model": "model-a",
            "content": "Acme is present.",
        },
    )
    assert response.status_code == 201
    assert client.post(f"/research/{research_id}/score").status_code == 200
    return research_id


def test_recommendation_api_generates_and_returns_latest_set(
    client: TestClient,
) -> None:
    research_id = _create_scored_research(client)

    generated = client.post(f"/research/{research_id}/recommendations")
    fetched = client.get(f"/research/{research_id}/recommendations")

    assert generated.status_code == 201
    assert fetched.status_code == 200
    assert fetched.json() == generated.json()
    assert {item["metric"] for item in generated.json()["recommendations"]} == {
        "citation_score",
        "recommendation_score",
    }


def test_recommendation_api_errors_and_openapi(client: TestClient) -> None:
    unscored = client.post("/research", json={"title": "Unscored"}).json()

    assert client.post(
        f"/research/{unscored['id']}/recommendations"
    ).status_code == 409
    assert client.post("/research/999999/recommendations").status_code == 404
    assert client.get(
        f"/research/{unscored['id']}/recommendations"
    ).status_code == 404
    path = "/research/{research_id}/recommendations"
    operations = client.get("/openapi.json").json()["paths"][path]
    assert {"get", "post"} <= operations.keys()
