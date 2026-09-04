from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from research.models import Research, ResearchScore

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient]:
    Base.metadata.create_all(test_engine)
    monkeypatch.setattr(
        "backend.app.main.hydrate_provider_credentials",
        lambda *_args, **_kwargs: None,
    )

    def override_get_db() -> Generator[Session]:
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)


def _create_task(client: TestClient, research_id: int, model: str) -> int:
    response = client.post(
        "/research-tasks",
        json={
            "research_id": research_id,
            "query": "Compare Acme",
            "provider": "test",
            "model": model,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _normalized(
    content: str,
    *,
    citations: list[dict] | None = None,
    metadata: dict | None = None,
) -> dict:
    return {
        "content": content,
        "citations": citations or [],
        "finish_reason": "stop",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 10,
            "total_tokens": 20,
            "cost": 0.01,
            "currency": "USD",
        },
        "metadata": metadata or {},
    }


def test_score_is_calculated_automatically_after_all_responses(
    client: TestClient,
) -> None:
    research_id = client.post(
        "/research",
        json={
            "title": "Acme visibility",
            "metadata": {"target_entity": "Acme"},
        },
    ).json()["id"]
    first_task = _create_task(client, research_id, "model-a")
    second_task = _create_task(client, research_id, "model-b")
    with TestingSession() as db:
        research = db.get(Research, research_id)
        assert research is not None
        research.total_tasks = 2
        db.commit()

    first = client.post(
        "/responses",
        json={
            "research_task_id": first_task,
            "provider": "test",
            "model": "model-a",
            "content": "Acme is recommended.",
            "normalized_response": _normalized(
                "Acme is recommended.",
                citations=[
                    {"url": "https://one.example"},
                    {"url": "https://two.example"},
                    {"url": "https://three.example"},
                ],
                metadata={
                    "brands": [{"name": "Acme", "confidence": 0.8}],
                    "recommendations": ["Choose Acme"],
                },
            ),
        },
    )
    assert first.status_code == 201
    assert client.get(f"/research/{research_id}/score").status_code == 404

    second = client.post(
        "/responses",
        json={
            "research_task_id": second_task,
            "provider": "test",
            "model": "model-b",
            "content": "A different provider is discussed.",
            "normalized_response": _normalized("A different provider is discussed."),
        },
    )
    assert second.status_code == 201

    score_response = client.get(f"/research/{research_id}/score")
    assert score_response.status_code == 200
    score = score_response.json()
    assert score["mention_score"] == 50.0
    assert score["recommendation_score"] == 50.0
    assert score["citation_score"] == 50.0
    assert score["coverage_score"] == 100.0
    assert score["confidence_score"] == 79.0
    assert score["visibility_score"] == 62.9
    assert score["version"] == "1.2"


def test_score_api_recalculates_same_version_without_duplicates(
    client: TestClient,
) -> None:
    research_id = client.post(
        "/research",
        json={"title": "Acme", "metadata": {"target_entity": "Acme"}},
    ).json()["id"]
    task_id = _create_task(client, research_id, "model-a")
    created = client.post(
        "/responses",
        json={
            "research_task_id": task_id,
            "provider": "test",
            "model": "model-a",
            "content": "Acme is present.",
        },
    )
    assert created.status_code == 201

    first = client.post(f"/research/{research_id}/score")
    second = client.post(f"/research/{research_id}/score")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["version"] == "1.2"
    with TestingSession() as db:
        scores = list(
            db.scalars(select(ResearchScore).where(ResearchScore.research_id == research_id))
        )
        assert len(scores) == 1


def test_scoring_errors_and_openapi(client: TestClient) -> None:
    research_id = client.post(
        "/research",
        json={"title": "No responses"},
    ).json()["id"]

    assert client.post(f"/research/{research_id}/score").status_code == 409
    assert client.get(f"/research/{research_id}/score").status_code == 404
    assert client.post("/research/999999/score").status_code == 404
    paths = client.get("/openapi.json").json()["paths"]
    assert "/research/{research_id}/score" in paths


def test_generic_product_recommendation_does_not_count_as_brand_recommendation(
    client: TestClient,
) -> None:
    research_id = client.post(
        "/research",
        json={"title": "Acme", "metadata": {"target_entity": "Acme"}},
    ).json()["id"]
    task_id = _create_task(client, research_id, "model-a")
    with TestingSession() as db:
        research = db.get(Research, research_id)
        assert research is not None
        research.total_tasks = 1
        db.commit()

    created = client.post(
        "/responses",
        json={
            "research_task_id": task_id,
            "provider": "test",
            "model": "model-a",
            "content": "Для чувствительной кожи рекомендую увлажняющую сыворотку.",
            "normalized_response": _normalized(
                "Для чувствительной кожи рекомендую увлажняющую сыворотку.",
                metadata={"recommendations": ["Выберите увлажняющую сыворотку"]},
            ),
        },
    )

    assert created.status_code == 201
    score = client.get(f"/research/{research_id}/score").json()
    assert score["recommendation_score"] == 0.0
