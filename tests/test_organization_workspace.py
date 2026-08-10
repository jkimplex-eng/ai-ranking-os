from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from organization_workspace.dependencies import user_id

engine = create_engine(
    "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client() -> Generator[TestClient]:
    Base.metadata.create_all(engine)

    def override_db() -> Generator[Session]:
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[user_id] = lambda: 1
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_organization_members_invites_projects_and_activity(client: TestClient) -> None:
    created = client.post(
        "/organizations",
        json={
            "name": "Разум Маркета",
            "slug": "razum-marketa",
            "country": "RU",
            "timezone": "Europe/Moscow",
        },
    )
    assert created.status_code == 201
    organization_id = created.json()["id"]
    assert created.json()["role"] == "OWNER"
    assert created.json()["is_default"] is True
    project_id = client.post("/workspace/projects", json={"name": "AI Ranking OS"}).json()["id"]
    assert client.post(
        f"/organizations/{organization_id}/projects", json={"project_id": project_id}
    ).json() == [project_id]
    invitation = client.post(
        f"/organizations/{organization_id}/invitations",
        json={"email": "analyst@example.com", "role": "MEMBER"},
    )
    assert invitation.status_code == 201
    token = invitation.json()["token"]

    app.dependency_overrides[user_id] = lambda: 2
    accepted = client.post("/organizations/invitations/accept", json={"token": token})
    assert accepted.status_code == 200
    assert accepted.json()["role"] == "MEMBER"
    assert client.post(f"/organizations/{organization_id}/switch").status_code == 200

    app.dependency_overrides[user_id] = lambda: 1
    members = client.get(f"/organizations/{organization_id}/members").json()
    second = next(item for item in members if item["user_id"] == 2)
    changed = client.patch(
        f"/organizations/{organization_id}/members/{second['id']}", json={"role": "ADMIN"}
    )
    assert changed.json()["role"] == "ADMIN"
    updated = client.patch(
        f"/organizations/{organization_id}", json={"limits": {"members": 20, "projects": 50}}
    )
    assert updated.json()["limits"]["members"] == 20
    actions = [
        item["action"] for item in client.get(f"/organizations/{organization_id}/activity").json()
    ]
    assert {
        "ORGANIZATION_CREATED",
        "MEMBER_INVITED",
        "INVITATION_ACCEPTED",
        "ROLE_CHANGED",
        "PROJECT_LINKED",
    } <= set(actions)
    assert "/organizations/{organization_id}/members" in client.get("/openapi.json").json()["paths"]
