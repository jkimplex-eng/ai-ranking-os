from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

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


def _create_scored_research(
    client: TestClient,
    *,
    entity_id: UUID,
    visibility: float,
    created_at: datetime,
) -> int:
    research = client.post(
        "/research",
        json={
            "entity_id": str(entity_id),
            "title": f"Research {visibility}",
            "metadata": {"target_entity": "Acme"},
        },
    )
    assert research.status_code == 201
    research_id = research.json()["id"]
    task = client.post(
        "/research-tasks",
        json={
            "research_id": research_id,
            "query": "Acme",
            "provider": "test",
            "model": f"model-{visibility}",
        },
    )
    assert task.status_code == 201
    response = client.post(
        "/responses",
        json={
            "research_task_id": task.json()["id"],
            "provider": "test",
            "model": f"model-{visibility}",
            "content": "Acme is present.",
        },
    )
    assert response.status_code == 201
    score = client.post(f"/research/{research_id}/score")
    assert score.status_code == 200
    with TestingSession() as db:
        stored_research = db.get(Research, research_id)
        stored_score = db.scalar(
            select(ResearchScore).where(
                ResearchScore.research_id == research_id
            )
        )
        assert stored_research is not None
        assert stored_score is not None
        stored_research.created_at = created_at
        stored_score.calculated_at = created_at
        stored_score.visibility_score = visibility
        db.commit()
    return research_id


def test_history_is_sorted_paginated_and_aggregated(
    client: TestClient,
) -> None:
    entity_id = uuid4()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    oldest_id = _create_scored_research(
        client,
        entity_id=entity_id,
        visibility=20,
        created_at=start,
    )
    middle_id = _create_scored_research(
        client,
        entity_id=entity_id,
        visibility=50,
        created_at=start + timedelta(days=1),
    )
    newest_id = _create_scored_research(
        client,
        entity_id=entity_id,
        visibility=80,
        created_at=start + timedelta(days=2),
    )
    _create_scored_research(
        client,
        entity_id=uuid4(),
        visibility=100,
        created_at=start + timedelta(days=3),
    )

    response = client.get(
        "/research/history",
        params={"entity_id": str(entity_id), "limit": 2},
    )

    assert response.status_code == 200
    history = response.json()
    assert [item["research_id"] for item in history["items"]] == [
        newest_id,
        middle_id,
    ]
    assert all(item["score_version"] == "1.2" for item in history["items"])
    assert all(item["model_count"] == 1 for item in history["items"])
    assert all(
        item["processed_response_count"] == 1 for item in history["items"]
    )
    assert history["aggregates"] == {
        "best_visibility": 80.0,
        "latest_visibility": 80.0,
        "average_visibility": 50.0,
        "research_count": 3,
        "first_to_latest_change": 60.0,
    }
    assert history["pagination"] == {"offset": 0, "limit": 2, "total": 3}

    next_page = client.get(
        "/research/history",
        params={"entity_id": str(entity_id), "offset": 2, "limit": 2},
    )
    assert next_page.status_code == 200
    assert [item["research_id"] for item in next_page.json()["items"]] == [
        oldest_id
    ]


def test_history_supports_empty_results_and_validation(
    client: TestClient,
) -> None:
    entity_id = uuid4()

    response = client.get(
        "/research/history",
        params={"entity_id": str(entity_id)},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["aggregates"] == {
        "best_visibility": None,
        "latest_visibility": None,
        "average_visibility": None,
        "research_count": 0,
        "first_to_latest_change": None,
    }
    assert client.get(
        "/research/history",
        params={"entity_id": "not-a-uuid"},
    ).status_code == 422
    assert client.get(
        "/research/history",
        params={"entity_id": str(entity_id), "limit": 0},
    ).status_code == 422


def test_history_openapi_contract(client: TestClient) -> None:
    path = "/research/history"
    operation = client.get("/openapi.json").json()["paths"][path]["get"]

    assert {item["name"] for item in operation["parameters"]} == {
        "entity_id",
        "offset",
        "limit",
    }
    schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert schema["$ref"].endswith("/ResearchHistoryRead")
