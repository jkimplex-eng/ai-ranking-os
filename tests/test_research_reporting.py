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


def _create_research(client: TestClient) -> tuple[int, int]:
    research = client.post(
        "/research",
        json={
            "title": "Acme visibility",
            "metadata": {"target_entity": "Acme"},
        },
    )
    assert research.status_code == 201
    research_id = research.json()["id"]
    task = client.post(
        "/research-tasks",
        json={
            "research_id": research_id,
            "query": "Is Acme recommended?",
            "provider": "test",
            "model": "model-a",
        },
    )
    assert task.status_code == 201
    return research_id, task.json()["id"]


def test_report_aggregates_all_research_results(client: TestClient) -> None:
    research_id, task_id = _create_research(client)
    response = client.post(
        "/responses",
        json={
            "research_task_id": task_id,
            "provider": "test",
            "model": "model-a",
            "content": "Acme is recommended.",
            "normalized_response": {
                "content": "Acme is recommended.",
                "citations": [
                    {
                        "url": "https://example.com/acme",
                        "title": "Acme Review",
                    }
                ],
                "finish_reason": "stop",
                "usage": {
                    "input_tokens": 5,
                    "output_tokens": 5,
                    "total_tokens": 10,
                    "cost": 0.01,
                    "currency": "USD",
                },
                "metadata": {
                    "brands": ["Acme"],
                    "recommendations": ["Choose Acme"],
                },
            },
        },
    )
    assert response.status_code == 201
    assert client.post(f"/research/{research_id}/score").status_code == 200

    report_response = client.get(f"/research/{research_id}/report")

    assert report_response.status_code == 200
    report = report_response.json()
    assert set(report) == {
        "research",
        "score",
        "responses",
        "entities",
        "citations",
        "recommendations",
    }
    assert report["research"]["id"] == research_id
    assert report["score"]["version"] == "1.0"
    assert report["responses"][0]["id"] == response.json()["id"]
    assert {item["name"] for item in report["entities"]} == {"Acme"}
    assert report["citations"][0]["url"] == "https://example.com/acme"
    assert report["recommendations"][0]["content"] == "Choose Acme"


def test_report_is_read_only_and_handles_missing_data(
    client: TestClient,
) -> None:
    research_id, _ = _create_research(client)

    first = client.get(f"/research/{research_id}/report")
    second = client.get(f"/research/{research_id}/report")

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["score"] is None
    assert first.json()["responses"] == []
    assert first.json()["entities"] == []
    assert first.json()["citations"] == []
    assert first.json()["recommendations"] == []
    assert client.get("/research/999999/report").status_code == 404


def test_report_openapi_contract(client: TestClient) -> None:
    path = "/research/{research_id}/report"
    openapi = client.get("/openapi.json").json()

    assert path in openapi["paths"]
    schema = openapi["paths"][path]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert schema["$ref"].endswith("/ResearchReportRead")
