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


def test_competitor_management_and_idempotent_import(client: TestClient) -> None:
    project_id = client.post("/workspace/projects", json={"name": "Client"}).json()["id"]
    created = client.post(
        f"/workspace/projects/{project_id}/competitors",
        json={
            "name": "Competitor A",
            "domains": ["competitor.example"],
            "brands": ["Competitor"],
        },
    )
    assert created.status_code == 201
    competitor_id = created.json()["id"]
    assert client.patch(
        f"/workspace/projects/{project_id}/competitors/{competitor_id}",
        json={"notes": "Track weekly"},
    ).json()["notes"] == "Track weekly"

    imported = client.post(
        f"/workspace/projects/{project_id}/competitors/import",
        json={
            "competitors": [
                {
                    "name": "Competitor A",
                    "domains": ["new.example"],
                    "brands": ["A"],
                },
                {"name": "Competitor B", "domains": ["b.example"]},
            ]
        },
    )
    assert imported.status_code == 200
    assert len(imported.json()) == 2
    assert next(item for item in imported.json() if item["id"] == competitor_id)["domains"] == [
        "new.example"
    ]
    assert client.delete(
        f"/workspace/projects/{project_id}/competitors/{competitor_id}"
    ).status_code == 204


def test_multi_domain_management_and_research_binding(client: TestClient) -> None:
    project_id = client.post("/workspace/projects", json={"name": "Portfolio"}).json()["id"]
    primary = client.post(
        f"/workspace/projects/{project_id}/domains",
        json={"hostname": "https://разуммаркета.рф/path", "brands": ["Разум Маркета"]},
    )
    assert primary.status_code == 201
    assert primary.json()["hostname"].startswith("xn--")
    assert primary.json()["is_primary"] is True
    secondary = client.post(
        f"/workspace/projects/{project_id}/domains",
        json={"hostname": "app.разуммаркета.рф", "is_primary": True},
    )
    assert secondary.status_code == 201
    domains = client.get(f"/workspace/projects/{project_id}/domains").json()
    assert len(domains) == 2
    assert sum(item["is_primary"] for item in domains) == 1
    assert next(item for item in domains if item["id"] == primary.json()["id"])[
        "is_primary"
    ] is False

    research = client.post(
        "/research",
        json={
            "project_id": project_id,
            "domain_id": secondary.json()["id"],
            "title": "Domain GEO audit",
        },
    )
    assert research.status_code == 201
    assert research.json()["domain_id"] == secondary.json()["id"]
    assert client.post(
        f"/workspace/projects/{project_id}/domains", json={"hostname": "not-a-domain"}
    ).status_code == 422


def test_research_templates_2_are_extensible(client: TestClient) -> None:
    created = client.post(
        "/research/templates",
        json={
            "code": "daily-geo-client",
            "title": "Daily GEO Client",
            "research_type": "GEO_AUDIT",
            "prompt_code": "ai-visibility",
            "pipeline": ["provider", "scoring", "report"],
            "default_languages": ["ru"],
            "configuration": {"routing_profile": "BALANCED"},
        },
    )
    assert created.status_code == 201
    assert created.json()["research_type"] == "GEO_AUDIT"
    cloned = client.post("/research/templates/daily-geo-client/clone")
    assert cloned.status_code == 201
    assert cloned.json()["version"] == 2
    updated = client.patch(
        "/research/templates/daily-geo-client",
        json={"configuration": {"routing_profile": "PRIVATE"}},
    )
    assert updated.status_code == 200
    assert updated.json()["configuration"]["routing_profile"] == "PRIVATE"
    assert client.post(
        "/research/templates",
        json={
            "code": "invalid-type",
            "title": "Invalid",
            "research_type": "UNKNOWN",
            "prompt_code": "ai-visibility",
            "pipeline": ["report"],
        },
    ).status_code == 422


def test_saved_configuration_crud_and_durable_launch(client: TestClient) -> None:
    project_id = client.post(
        "/workspace/projects", json={"name": "Skinjestique"}
    ).json()["id"]
    domain_id = client.post(
        f"/workspace/projects/{project_id}/domains",
        json={"hostname": "skinjestique.example"},
    ).json()["id"]
    base_url = f"/workspace/projects/{project_id}/configurations"

    created = client.post(
        base_url,
        json={
            "name": "Weekly visibility",
            "template_code": "ai-visibility",
            "routing_profile": "BALANCED",
            "languages": ["ru", "en"],
            "regions": ["RU"],
            "prompt_count": 6,
            "schedule_hint": "weekly",
        },
    )
    assert created.status_code == 201
    configuration_id = created.json()["id"]
    assert client.get(base_url).json()[0]["prompt_count"] == 6

    updated = client.patch(
        f"{base_url}/{configuration_id}",
        json={"routing_profile": "HIGH_QUALITY", "prompt_count": 8},
    )
    assert updated.status_code == 200
    assert updated.json()["routing_profile"] == "HIGH_QUALITY"

    launched = client.post(
        f"{base_url}/{configuration_id}/run",
        json={
            "domain_id": domain_id,
            "title": "Skinjestique weekly visibility",
            "query": "Where is Skinjestique visible in AI answers?",
        },
    )
    assert launched.status_code == 202
    assert launched.json()["state"] == "PENDING"
    research = client.get(f"/research/{launched.json()['research_id']}")
    assert research.status_code == 200
    assert research.json()["project_id"] == project_id
    assert research.json()["domain_id"] == domain_id

    assert client.delete(f"{base_url}/{configuration_id}").status_code == 204
    assert client.get(base_url).json() == []
