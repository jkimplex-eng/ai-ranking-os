from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from decision_center.models import ExecutionLog

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


def create_agent(client: TestClient, name: str = "Research Agent") -> dict:
    response = client.post("/agents", json={"name": name, "description": "Ranks evidence"})
    assert response.status_code == 201
    return response.json()


def create_task(
    client: TestClient,
    title: str,
    *,
    status: str = "BACKLOG",
    owner_id: int | None = None,
) -> dict:
    payload = {"title": title, "status": status, "owner_id": owner_id}
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    return response.json()


def test_task_crud_and_assignment(client: TestClient) -> None:
    agent = create_agent(client)
    sprint_response = client.post(
        "/sprints",
        json={
            "name": "Sprint 1",
            "goal": "Ship Decision Center",
            "starts_on": "2026-07-29",
            "ends_on": "2026-08-12",
        },
    )
    assert sprint_response.status_code == 201
    sprint = sprint_response.json()

    task = create_task(client, "Implement API", status="READY")
    task_id = task["id"]

    assign_response = client.post(
        f"/tasks/{task_id}/assign",
        json={"agent_id": agent["id"]},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["owner_id"] == agent["id"]

    patch_response = client.patch(
        f"/tasks/{task_id}",
        json={
            "description": "Implement all Decision Center endpoints",
            "status": "IN_PROGRESS",
            "sprint_id": sprint["id"],
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "IN_PROGRESS"
    assert patch_response.json()["sprint_id"] == sprint["id"]

    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Implement API"

    list_response = client.get("/tasks")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [task_id]

    assert client.get("/agents").json()[0]["id"] == agent["id"]
    assert client.get("/sprints").json()[0]["id"] == sprint["id"]


def test_agent_cannot_have_two_in_progress_tasks(client: TestClient) -> None:
    agent = create_agent(client)
    first = create_task(client, "First", status="READY", owner_id=agent["id"])
    second = create_task(client, "Second", status="READY", owner_id=agent["id"])

    first_response = client.patch(
        f"/tasks/{first['id']}",
        json={"status": "IN_PROGRESS"},
    )
    assert first_response.status_code == 200

    second_response = client.patch(
        f"/tasks/{second['id']}",
        json={"status": "IN_PROGRESS"},
    )
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Agent already has an IN_PROGRESS task"


def test_task_can_only_complete_from_review(client: TestClient) -> None:
    task = create_task(client, "Review gate", status="IN_PROGRESS")

    early_complete = client.post(f"/tasks/{task['id']}/complete")
    assert early_complete.status_code == 409

    direct_done = client.patch(f"/tasks/{task['id']}", json={"status": "DONE"})
    assert direct_done.status_code == 409

    review_response = client.patch(f"/tasks/{task['id']}", json={"status": "REVIEW"})
    assert review_response.status_code == 200

    complete_response = client.post(f"/tasks/{task['id']}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "DONE"


def test_every_mutation_is_written_to_execution_log(client: TestClient) -> None:
    agent = create_agent(client, "Logging Agent")
    task = create_task(client, "Audited task", status="READY")
    client.post(f"/tasks/{task['id']}/assign", json={"agent_id": agent["id"]})
    client.patch(f"/tasks/{task['id']}", json={"status": "REVIEW"})
    client.post(f"/tasks/{task['id']}/complete")
    client.post("/sprints", json={"name": "Audited sprint"})

    with TestingSession() as session:
        count = session.scalar(select(func.count()).select_from(ExecutionLog))
        actions = list(
            session.scalars(select(ExecutionLog.action).order_by(ExecutionLog.id))
        )

    assert count == 6
    assert actions == ["CREATE", "CREATE", "ASSIGN", "UPDATE", "COMPLETE", "CREATE"]


def test_missing_entities_and_input_validation(client: TestClient) -> None:
    assert client.get("/tasks/999").status_code == 404
    assert client.post("/tasks", json={"title": ""}).status_code == 422
    assert (
        client.post(
            "/sprints",
            json={
                "name": "Invalid dates",
                "starts_on": "2026-08-12",
                "ends_on": "2026-07-29",
            },
        ).status_code
        == 422
    )

