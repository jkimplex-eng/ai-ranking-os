from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from recommendation.models import RecommendationPriority, RecommendationRule
from recommendation.templates.models import RecommendationTemplate

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)

TEMPLATE_DEFINITIONS = (
    ("mention-plan", "MENTION_GROWTH", RecommendationPriority.HIGH),
    ("citation-plan", "CITATION_AUTHORITY", RecommendationPriority.HIGH),
    ("trust-plan", "TRUST_SIGNALS", RecommendationPriority.CRITICAL),
    ("coverage-plan", "SOURCE_EXPANSION", RecommendationPriority.MEDIUM),
)
RULE_DEFINITIONS = (
    ("mention", "MENTION_GROWTH", "mention_score", 60),
    ("citation", "CITATION_AUTHORITY", "citation_score", 50),
    ("trust", "TRUST_SIGNALS", "recommendation_score", 60),
    ("coverage", "SOURCE_EXPANSION", "coverage_score", 70),
)


def _seed(db: Session) -> None:
    priority_by_type = {
        recommendation_type: priority
        for _, recommendation_type, priority in TEMPLATE_DEFINITIONS
    }
    db.add_all(
        [
            RecommendationTemplate(
                template_code=code,
                recommendation_type=recommendation_type,
                title=f"{recommendation_type} action plan",
                description="A concrete plan.",
                steps=["Audit the baseline.", "Apply changes.", "Measure again."],
                expected_result=f"Improve {recommendation_type}.",
                estimated_time="2-4 weeks",
                priority=priority,
                version="1.0",
            )
            for code, recommendation_type, priority in TEMPLATE_DEFINITIONS
        ]
    )
    db.add_all(
        [
            RecommendationRule(
                code=f"v1-{code}",
                recommendation_type=recommendation_type,
                metric=metric,
                operator="lt",
                threshold=threshold,
                priority=priority_by_type[recommendation_type],
                explanation_template=(
                    "{metric} is {metric_value}, below {threshold}."
                ),
                expected_effect=f"Increase {metric}.",
                version="1.0",
                is_active=True,
            )
            for code, recommendation_type, metric, threshold in RULE_DEFINITIONS
        ]
    )
    db.commit()


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


def test_template_read_only_api_and_version_resolution(
    client: TestClient,
) -> None:
    templates = client.get("/recommendation/templates")

    assert templates.status_code == 200
    assert len(templates.json()) == 4
    assert all(item["version"] == "1.0" for item in templates.json())
    template = client.get("/recommendation/templates/trust-plan")
    assert template.status_code == 200
    assert template.json()["steps"]
    assert template.json()["estimated_time"] == "2-4 weeks"
    assert client.get(
        "/recommendation/templates/missing"
    ).status_code == 404


def test_generation_binds_templates_and_builds_action_plan(
    client: TestClient,
) -> None:
    research_id = _create_scored_research(client)
    generated = client.post(f"/research/{research_id}/recommendations")

    assert generated.status_code == 201
    assert generated.json()["recommendations"]
    assert all(
        item["template_id"] is not None
        for item in generated.json()["recommendations"]
    )
    first = client.get(f"/research/{research_id}/action-plan")
    second = client.get(f"/research/{research_id}/action-plan")

    assert first.status_code == 200
    assert first.json() == second.json()
    plan = first.json()
    assert plan["recommendation_execution_id"] == generated.json()[
        "execution_id"
    ]
    assert len(plan["items"]) == len(generated.json()["recommendations"])
    assert all(item["template"] is not None for item in plan["items"])
    assert all(len(item["steps"]) == 3 for item in plan["items"])
    assert all(item["expected_effect"] for item in plan["items"])
    assert all(item["estimated_time"] == "2-4 weeks" for item in plan["items"])


def test_action_plan_errors_and_openapi(client: TestClient) -> None:
    research = client.post("/research", json={"title": "No plan"}).json()

    assert client.get(
        f"/research/{research['id']}/action-plan"
    ).status_code == 404
    paths = client.get("/openapi.json").json()["paths"]
    assert "/recommendation/templates" in paths
    assert "/recommendation/templates/{code}" in paths
    assert "/research/{research_id}/action-plan" in paths
