from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from research.models import Research, ResearchScore, ResearchStatus

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client() -> Generator[TestClient]:
    Base.metadata.create_all(engine)

    def override() -> Generator[Session]:
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_workspace_is_provisioned_and_aggregates_recent_work(client: TestClient) -> None:
    with TestingSession() as db:
        research = Research(title="Skinjestique daily", status=ResearchStatus.COMPLETED)
        db.add(research)
        db.flush()
        db.add(
            ResearchScore(
                research_id=research.id,
                mention_score=80,
                recommendation_score=90,
                citation_score=60,
                coverage_score=85,
                confidence_score=92,
                visibility_score=81.4,
                version="1.0",
            )
        )
        db.commit()

    response = client.get("/workspace")
    assert response.status_code == 200
    assert response.json()["total_research"] == 1
    assert response.json()["recent_research"][0]["title"] == "Skinjestique daily"
    assert response.json()["recent_reports"][0]["visibility_score"] == 81.4

    updated = client.patch("/workspace", json={"name": "AI Ranking Team"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "AI Ranking Team"
    assert "/workspace" in client.get("/openapi.json").json()["paths"]


def test_project_crud_and_research_ownership(client: TestClient) -> None:
    created = client.post(
        "/workspace/projects",
        json={"name": "Разум Маркета", "favorite": True, "tags": ["own-brand"]},
    )
    assert created.status_code == 201
    project_id = created.json()["id"]

    research = client.post(
        "/research",
        json={"project_id": project_id, "title": "GEO audit"},
    )
    assert research.status_code == 201
    assert research.json()["project_id"] == project_id

    detail = client.get(f"/workspace/projects/{project_id}")
    assert detail.status_code == 200
    assert detail.json()["research_count"] == 1
    assert client.get("/workspace").json()["favorite_projects"][0]["id"] == project_id

    updated = client.patch(
        f"/workspace/projects/{project_id}", json={"description": "Daily internal analysis"}
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Daily internal analysis"
    assert client.delete(f"/workspace/projects/{project_id}").status_code == 204
    assert client.get(f"/workspace/projects/{project_id}").status_code == 404
