from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from decision_center.models import AgentType
from execution_engine.worker_manager import WorkerManager

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


def test_research_api_acceptance_flow(client: TestClient) -> None:
    assert (
        client.post(
            "/agents",
            json={"name": "research-runner", "agent_type": "CODEX"},
        ).status_code
        == 201
    )
    created = client.post(
        "/research",
        json={
            "title": "AI Visibility Study",
            "objective": "Compare model presence",
            "metadata": {"region": "RUSSIA"},
        },
    )
    assert created.status_code == 201
    research_id = created.json()["id"]
    assert created.json()["status"] == "DRAFT"
    assert created.json()["metadata"] == {"region": "RUSSIA"}

    listed = client.get("/research", params={"offset": 0, "limit": 10})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [research_id]

    fetched = client.get(f"/research/{research_id}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "AI Visibility Study"

    updated = client.patch(
        f"/research/{research_id}",
        json={"title": "Updated Study", "description": "Validated"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated Study"

    started = client.post(
        f"/research/{research_id}/run",
        json={
            "models": [
                {"provider": "openai", "model": "gpt-4o-mini"},
                {"provider": "yandex", "model": "yandexgpt-pro"},
            ],
            "query": "Compare model visibility",
        },
    )
    assert started.status_code == 200
    assert started.json()["status"] == "COMPLETED"
    assert started.json()["total_tasks"] == 2
    assert started.json()["completed_tasks"] == 2
    assert started.json()["failed_tasks"] == 0
    assert started.json()["progress_percent"] == 100
    tasks = client.get(
        "/research-tasks",
        params={"research_id": research_id},
    ).json()
    assert len(tasks) == 2
    assert {task["status"] for task in tasks} == {"COMPLETED"}
    assert all(task["decision_task_id"] for task in tasks)
    assert all(task["execution_id"] for task in tasks)
    responses = client.get("/responses").json()
    assert len(responses) == 2
    assert {item["provider"] for item in responses} == {"openai", "yandex"}
    assert all(item["prompt"] == "Compare model visibility" for item in responses)
    assert all(item["raw_response"] for item in responses)
    assert all(item["normalized_response"]["finish_reason"] == "stop" for item in responses)
    assert all(item["normalized_response"]["content"] for item in responses)
    assert all(item["input_tokens"] > 0 for item in responses)
    assert all(item["output_tokens"] > 0 for item in responses)
    assert all(
        item["total_tokens"] == item["input_tokens"] + item["output_tokens"]
        for item in responses
    )
    assert all(item["cost"] >= 0 for item in responses)
    assert all(item["finished_at"] for item in responses)
    assert all(item["error_type"] is None for item in responses)

    deleted = client.delete(f"/research/{research_id}")
    assert deleted.status_code == 204
    assert client.get(f"/research/{research_id}").status_code == 404


def test_research_api_validation_and_errors(client: TestClient) -> None:
    assert client.post("/research", json={"title": ""}).status_code == 422
    assert client.post("/research", json={"title": "x" * 301}).status_code == 422
    assert client.get("/research", params={"limit": 0}).status_code == 422
    assert client.get("/research/not-an-integer").status_code == 422
    assert client.get("/research/999").status_code == 404
    assert client.patch("/research/999", json={"title": "missing"}).status_code == 404
    assert client.delete("/research/999").status_code == 404
    run_payload = {
        "models": [{"provider": "openai", "model": "gpt-4o-mini"}]
    }
    assert client.post("/research/999/run", json=run_payload).status_code == 404
    assert client.post("/research/1/run", json={"models": []}).status_code == 422

    archived = client.post(
        "/research",
        json={"title": "Archived", "status": "ARCHIVED"},
    )
    research_id = archived.json()["id"]
    conflict = client.post(f"/research/{research_id}/run", json=run_payload)
    assert conflict.status_code == 409
    assert "cannot be run" in conflict.json()["detail"]


def test_research_run_marks_failures_and_progress(client: TestClient) -> None:
    research = client.post(
        "/research",
        json={"title": "No agents available"},
    ).json()
    response = client.post(
        f"/research/{research['id']}/run",
        json={
            "models": [
                {"provider": "openai", "model": "gpt-4o-mini"},
                {"provider": "yandex", "model": "yandexgpt-pro"},
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"
    assert response.json()["total_tasks"] == 2
    assert response.json()["completed_tasks"] == 0
    assert response.json()["failed_tasks"] == 2
    assert response.json()["progress_percent"] == 100
    tasks = client.get(
        "/research-tasks",
        params={"research_id": research["id"]},
    ).json()
    assert {task["status"] for task in tasks} == {"FAILED"}
    assert all("No compatible free agent" in task["error"] for task in tasks)
    assert {task["status"] for task in client.get("/tasks").json()} == {"BLOCKED"}
    responses = client.get("/responses").json()
    assert len(responses) == 2
    assert all(item["error_type"] == "provider_error" for item in responses)
    assert all(item["normalized_response"]["finish_reason"] == "error" for item in responses)
    assert all(item["error_message"] for item in responses)


@pytest.mark.parametrize(
    ("worker_result", "expected_error"),
    [
        (RuntimeError("provider unavailable"), "provider_error"),
        (TimeoutError("request timed out"), "timeout"),
        (ValueError("JSON parsing failed"), "parsing_error"),
        ({"unexpected": True}, "validation_error"),
    ],
)
def test_research_run_persists_each_error_category(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    worker_result: Exception | dict,
    expected_error: str,
) -> None:
    def execute(_task: object) -> dict:
        if isinstance(worker_result, Exception):
            raise worker_result
        return worker_result

    manager = WorkerManager({AgentType.CODEX: execute})
    monkeypatch.setattr(
        "research.service._provider_worker",
        lambda tasks, provider_factory: manager,
    )
    client.post(
        "/agents",
        json={"name": f"runner-{expected_error}", "agent_type": "CODEX"},
    )
    research = client.post(
        "/research",
        json={"title": expected_error},
    ).json()
    result = client.post(
        f"/research/{research['id']}/run",
        json={
            "models": [{"provider": "openai", "model": "gpt-4o-mini"}],
            "query": "trigger",
        },
    )
    assert result.status_code == 200
    assert result.json()["status"] == "FAILED"
    responses = client.get("/responses").json()
    assert len(responses) == 1
    assert responses[0]["error_type"] == expected_error
    assert responses[0]["normalized_response"]["finish_reason"] == "error"


def test_research_api_openapi_contract(client: TestClient) -> None:
    specification = client.get("/openapi.json").json()
    expected = {
        "/research": {"get", "post"},
        "/research/{research_id}": {"get", "patch", "delete"},
        "/research/{research_id}/run": {"post"},
    }
    for path, methods in expected.items():
        assert path in specification["paths"]
        assert methods <= set(specification["paths"][path])

    create_schema = specification["components"]["schemas"]["ResearchCreate"]
    assert "title" in create_schema["required"]
    assert create_schema["properties"]["title"]["maxLength"] == 300
