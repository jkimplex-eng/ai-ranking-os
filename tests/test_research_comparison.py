from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app

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


def _scored_research(
    client: TestClient,
    *,
    title: str,
    content: str,
    entities: list[str],
    recommendations: list[str],
    citations: list[dict],
) -> tuple[int, dict]:
    research = client.post(
        "/research",
        json={"title": title, "metadata": {"target_entity": "Acme"}},
    )
    assert research.status_code == 201
    research_id = research.json()["id"]
    task = client.post(
        "/research-tasks",
        json={
            "research_id": research_id,
            "query": title,
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
            "content": content,
            "normalized_response": {
                "content": content,
                "citations": citations,
                "finish_reason": "stop",
                "usage": {
                    "input_tokens": 5,
                    "output_tokens": 5,
                    "total_tokens": 10,
                    "cost": 0.01,
                    "currency": "USD",
                },
                "metadata": {
                    "brands": entities,
                    "recommendations": recommendations,
                },
            },
        },
    )
    assert response.status_code == 201
    score = client.post(f"/research/{research_id}/score")
    assert score.status_code == 200
    return research_id, score.json()


def test_compare_research_scores_and_intelligence_changes(
    client: TestClient,
) -> None:
    left_id, left_score = _scored_research(
        client,
        title="Baseline",
        content="Acme is not highlighted.",
        entities=["Acme", "Legacy"],
        recommendations=["Use Legacy"],
        citations=[],
    )
    right_id, right_score = _scored_research(
        client,
        title="Follow-up",
        content="Acme is recommended.",
        entities=["Acme", "Future"],
        recommendations=["Use Future"],
        citations=[
            {"url": "https://one.example"},
            {"url": "https://two.example"},
        ],
    )

    response = client.get(
        "/research/compare",
        params={"left": left_id, "right": right_id},
    )

    assert response.status_code == 200
    comparison = response.json()
    assert comparison["left_research_id"] == left_id
    assert comparison["right_research_id"] == right_id
    for metric in (
        "visibility_score",
        "mention_score",
        "recommendation_score",
        "citation_score",
        "coverage_score",
        "confidence_score",
    ):
        assert comparison[f"{metric}_delta"] == round(
            right_score[metric] - left_score[metric],
            2,
        )
    assert comparison["new_entities"] == ["Future"]
    assert comparison["disappeared_entities"] == ["Legacy"]
    assert comparison["new_recommendations"] == ["Use Future"]
    assert comparison["disappeared_recommendations"] == ["Use Legacy"]


def test_comparison_is_read_only_and_validates_inputs(
    client: TestClient,
) -> None:
    left_id, _ = _scored_research(
        client,
        title="Same",
        content="Acme",
        entities=["Acme"],
        recommendations=[],
        citations=[],
    )
    first = client.get(
        "/research/compare",
        params={"left": left_id, "right": left_id},
    )
    second = client.get(
        "/research/compare",
        params={"left": left_id, "right": left_id},
    )

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["visibility_score_delta"] == 0
    assert first.json()["new_entities"] == []
    assert first.json()["disappeared_entities"] == []
    assert client.get("/research/compare").status_code == 422
    assert client.get(
        "/research/compare",
        params={"left": left_id, "right": 999999},
    ).status_code == 404


def test_comparison_requires_scores_and_updates_openapi(
    client: TestClient,
) -> None:
    scored_id, _ = _scored_research(
        client,
        title="Scored",
        content="Acme",
        entities=["Acme"],
        recommendations=[],
        citations=[],
    )
    unscored = client.post("/research", json={"title": "Unscored"}).json()

    assert client.get(
        "/research/compare",
        params={"left": scored_id, "right": unscored["id"]},
    ).status_code == 409
    path = "/research/compare"
    openapi = client.get("/openapi.json").json()
    assert path in openapi["paths"]
    assert {"left", "right"} == {
        item["name"] for item in openapi["paths"][path]["get"]["parameters"]
    }
