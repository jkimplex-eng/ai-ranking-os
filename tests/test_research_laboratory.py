from collections.abc import Generator
from uuid import uuid4

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


def _research_with_response(
    client: TestClient, title: str, content: str, source: str
) -> tuple[int, int, str]:
    entity_id = str(uuid4())
    research = client.post(
        "/research",
        json={"title": title, "entity_id": entity_id, "metadata": {"target_entity": title}},
    )
    assert research.status_code == 201
    research_id = research.json()["id"]
    task = client.post(
        "/research-tasks",
        json={
            "research_id": research_id,
            "query": f"Tell me about {title}",
            "provider": "openai",
            "model": "gpt-test",
        },
    )
    response = client.post(
        "/responses",
        json={
            "research_task_id": task.json()["id"],
            "provider": "openai",
            "model": "gpt-test",
            "content": content,
            "prompt": f"Tell me about {title}",
            "normalized_response": {
                "content": content,
                "citations": [{"url": source, "title": "Independent source"}],
                "finish_reason": "stop",
                "usage": {
                    "input_tokens": 2,
                    "output_tokens": 3,
                    "total_tokens": 5,
                    "cost": 0,
                    "currency": "USD",
                },
                "metadata": {"brands": [title], "recommendations": [f"Choose {title}"]},
            },
        },
    )
    assert response.status_code == 201
    assert client.post(f"/research/{research_id}/score").status_code == 200
    return research_id, response.json()["id"], entity_id


def test_laboratory_exposes_exact_provenance_without_model_score(client: TestClient) -> None:
    research_id, _, _ = _research_with_response(
        client, "Acme", "Acme is recommended by the model.", "https://example.com/acme"
    )

    response = client.get(f"/research/{research_id}/laboratory")

    assert response.status_code == 200
    payload = response.json()
    assert payload["models"][0]["prompt"] == "Tell me about Acme"
    assert payload["models"][0]["signals"]["mentioned"] is True
    assert payload["models"][0]["signals"]["visibility_score"] is None
    assert (
        payload["models"][0]["signals"]["visibility_status"]
        == "NOT_CALCULATED_PER_MODEL_IN_SCORING_V1"
    )
    assert payload["sources"][0]["domain"] == "example.com"
    assert payload["sources"][0]["authority"] is None
    assert payload["graph"]["status"] == "NOT_LINKED"
    assert {event["type"] for event in payload["timeline"]} >= {
        "RESEARCH_CREATED",
        "TASK_CREATED",
        "RESPONSE_FINISHED",
        "SCORE_CALCULATED",
    }


def test_diff_compares_persisted_artifacts_and_labels_non_causality(client: TestClient) -> None:
    left, _, _ = _research_with_response(client, "Acme", "Acme appears.", "https://old.example/a")
    right, _, _ = _research_with_response(
        client, "Acme", "Acme is recommended.", "https://new.example/a"
    )

    response = client.get("/research/diff", params={"left": left, "right": right})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_changes"] == {
        "added": ["https://new.example/a"],
        "removed": ["https://old.example/a"],
    }
    assert "not causal" in payload["interpretation"]
    assert client.get("/research/diff", params={"left": 9999, "right": right}).status_code == 404


def test_publication_keeps_earliest_observation_and_is_in_timeline(client: TestClient) -> None:
    research_id, response_id, entity_id = _research_with_response(
        client, "Acme", "Acme cites the publication.", "https://publisher.example/article"
    )
    publication = client.post(
        "/research-publications",
        json={
            "entity_id": entity_id,
            "research_id": research_id,
            "url": "https://publisher.example/article",
            "content_hash": "a" * 64,
            "title": "Acme independent study",
            "published_at": "2026-08-01T10:00:00Z",
        },
    )
    assert publication.status_code == 201
    publication_id = publication.json()["id"]
    later = {
        "research_id": research_id,
        "response_id": response_id,
        "provider": "openai",
        "model": "gpt-test",
        "first_observed_at": "2026-08-05T10:00:00Z",
        "evidence_excerpt": "Later observation",
    }
    assert (
        client.post(f"/research-publications/{publication_id}/observations", json=later).status_code
        == 201
    )
    earlier = {
        **later,
        "first_observed_at": "2026-08-03T10:00:00Z",
        "evidence_excerpt": "Earlier proof",
    }
    saved = client.post(f"/research-publications/{publication_id}/observations", json=earlier)
    assert saved.status_code == 201
    assert saved.json()["first_observed_at"].startswith("2026-08-03T10:00:00")
    assert saved.json()["evidence_excerpt"] == "Earlier proof"
    listed = client.get("/research-publications", params={"entity_id": entity_id})
    assert len(listed.json()[0]["observations"]) == 1
    laboratory = client.get(f"/research/{research_id}/laboratory").json()
    assert "FIRST_OBSERVED" in {event["type"] for event in laboratory["timeline"]}


def test_research_laboratory_openapi_contract(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/research/{research_id}/laboratory" in paths
    assert "/research/diff" in paths
    assert "/research-publications/{publication_id}/observations" in paths
