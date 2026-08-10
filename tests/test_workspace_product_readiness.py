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


def test_bulk_research_uses_common_queue_and_returns_summary(client: TestClient) -> None:
    project_id = client.post(
        "/workspace/projects", json={"name": "Brand portfolio"}
    ).json()["id"]
    domain_id = client.post(
        f"/workspace/projects/{project_id}/domains",
        json={"hostname": "skinjestique.ru"},
    ).json()["id"]
    url = f"/workspace/projects/{project_id}/bulk-research"
    created = client.post(
        url,
        json={
            "name": "Weekly portfolio",
            "template_code": "geo-analysis",
            "routing_profile": "BALANCED",
            "languages": ["ru"],
            "regions": ["RU"],
            "targets": [
                {"brand": "Skinjestique", "domain_id": domain_id},
                {"brand": "Разум Маркета"},
                {"brand": "AI Ranking OS"},
            ],
        },
    )
    assert created.status_code == 202
    report = created.json()
    assert report["total_items"] == 3
    assert report["pending_items"] == 3
    assert report["progress_percent"] == 0
    assert len({item["job_id"] for item in report["items"]}) == 3
    assert len({item["research_id"] for item in report["items"]}) == 3

    run_id = report["id"]
    assert client.get(f"{url}/{run_id}").json()["name"] == "Weekly portfolio"
    assert len(client.get(url).json()) == 1
    duplicate = client.post(
        url,
        json={
            "name": "Invalid",
            "targets": [{"brand": "Same"}, {"brand": "Same"}],
        },
    )
    assert duplicate.status_code == 422


def test_report_center_search_tags_archive_and_json_export(client: TestClient) -> None:
    project_id = client.post(
        "/workspace/projects", json={"name": "Report portfolio"}
    ).json()["id"]
    research = client.post(
        "/research",
        json={"project_id": project_id, "title": "Skinjestique GEO Audit"},
    ).json()
    listing = client.get(
        "/reports", params={"project_id": project_id, "search": "skinjestique"}
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    tagged = client.patch(
        f"/reports/{research['id']}", json={"tags": ["weekly", "client"]}
    )
    assert tagged.status_code == 200
    assert tagged.json()["tags"] == ["weekly", "client"]
    assert client.get("/reports", params={"tag": "weekly"}).json()["total"] == 1

    exported = client.get(f"/reports/{research['id']}/export")
    assert exported.status_code == 200
    assert exported.json()["research"]["id"] == research["id"]
    assert "attachment" in exported.headers["content-disposition"]

    assert client.patch(
        f"/reports/{research['id']}", json={"archived": True}
    ).status_code == 200
    assert client.get("/reports").json()["total"] == 0
    assert client.get("/reports", params={"archived": True}).json()["total"] == 1


def test_report_versioning_is_immutable_deduplicated_and_comparable(
    client: TestClient,
) -> None:
    project_id = client.post(
        "/workspace/projects", json={"name": "Versioned reports"}
    ).json()["id"]
    research = client.post(
        "/research", json={"project_id": project_id, "title": "Weekly audit"}
    ).json()
    url = f"/reports/{research['id']}/versions"
    first = client.post(url)
    assert first.status_code == 200
    assert first.json()["version"] == 1
    assert client.post(url).json()["version"] == 1

    assert client.patch(
        f"/research/{research['id']}", json={"title": "Monthly audit"}
    ).status_code == 200
    second = client.post(url)
    assert second.json()["version"] == 2
    assert [item["version"] for item in client.get(url).json()] == [2, 1]
    comparison = client.get(
        f"{url}/compare", params={"left": 1, "right": 2}
    )
    assert comparison.status_code == 200
    assert comparison.json()["score_deltas"]["visibility_score"] is None


def test_report_sharing_public_private_rotation_revocation_and_audit(
    client: TestClient,
) -> None:
    project_id = client.post(
        "/workspace/projects", json={"name": "Shared reports"}
    ).json()["id"]
    research_id = client.post(
        "/research", json={"project_id": project_id, "title": "Client report"}
    ).json()["id"]
    shares_url = f"/reports/{research_id}/shares"

    public = client.post(shares_url, json={"access_mode": "PUBLIC"})
    assert public.status_code == 201
    public_token = public.json()["token"]
    opened = client.get(f"/shared/reports/{public_token}")
    assert opened.status_code == 200
    assert opened.json()["read_only"] is True
    assert opened.json()["report"]["research"]["id"] == research_id

    private = client.post(
        shares_url,
        json={"access_mode": "PRIVATE", "password": "client-secret-123"},
    )
    assert private.status_code == 201
    private_token = private.json()["token"]
    assert client.get(f"/shared/reports/{private_token}").status_code == 404
    assert client.get(
        f"/shared/reports/{private_token}",
        headers={"X-Share-Password": "client-secret-123"},
    ).status_code == 200

    rotated = client.post(f"/reports/shares/{private.json()['id']}/rotate")
    assert rotated.status_code == 200
    assert rotated.json()["token"] != private_token
    assert client.get(
        f"/shared/reports/{private_token}",
        headers={"X-Share-Password": "client-secret-123"},
    ).status_code == 404
    assert client.get(
        f"/shared/reports/{rotated.json()['token']}",
        headers={"X-Share-Password": "client-secret-123"},
    ).status_code == 200

    assert client.post(
        f"/reports/shares/{public.json()['id']}/revoke"
    ).status_code == 200
    assert client.get(f"/shared/reports/{public_token}").status_code == 404
    links = client.get(shares_url).json()
    assert sum(link["view_count"] for link in links) == 3
    audited = client.get(
        "/audit/events", params={"action": "report.share.viewed"}
    ).json()
    assert audited["total"] == 3


def test_project_monitoring_delegates_to_existing_scheduler(client: TestClient) -> None:
    project_id = client.post(
        "/workspace/projects", json={"name": "Monitored project"}
    ).json()["id"]
    template_id = client.post(
        "/research",
        json={"project_id": project_id, "title": "Weekly monitoring template"},
    ).json()["id"]
    url = f"/workspace/projects/{project_id}/monitoring"
    configured = client.put(
        url,
        json={
            "template_research_id": template_id,
            "frequency": "WEEKLY",
            "models": [{"provider": "openai", "model": "gpt-4o-mini"}],
            "query": "Track weekly AI visibility",
        },
    )
    assert configured.status_code == 200
    schedule_id = configured.json()["schedule_id"]
    schedules = client.get("/schedules").json()
    assert any(item["id"] == schedule_id for item in schedules)
    assert configured.json()["frequency"] == "WEEKLY"

    updated = client.put(
        url,
        json={
            "template_research_id": template_id,
            "frequency": "DAILY",
            "models": [{"provider": "gemini", "model": "gemini-2.5-flash"}],
            "enabled": False,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["frequency"] == "DAILY"
    assert updated.json()["enabled"] is False
    assert client.get(url).json()["schedule_id"] == schedule_id

    other_project = client.post(
        "/workspace/projects", json={"name": "Other project"}
    ).json()["id"]
    assert client.put(
        f"/workspace/projects/{other_project}/monitoring",
        json={
            "template_research_id": template_id,
            "frequency": "MONTHLY",
            "models": [{"provider": "openai", "model": "gpt-4o-mini"}],
        },
    ).status_code == 422
    assert client.delete(url).status_code == 204
    assert not any(item["id"] == schedule_id for item in client.get("/schedules").json())


def test_change_detection_persists_metric_and_graph_deltas(client: TestClient) -> None:
    project_id = client.post(
        "/workspace/projects", json={"name": "Changing project"}
    ).json()["id"]
    with TestingSession() as db:
        previous = Research(
            project_id=project_id,
            title="Previous",
            status=ResearchStatus.COMPLETED,
        )
        current = Research(
            project_id=project_id,
            title="Current",
            status=ResearchStatus.COMPLETED,
        )
        db.add_all([previous, current])
        db.flush()
        db.add_all(
            [
                ResearchScore(
                    research_id=previous.id,
                    mention_score=70,
                    recommendation_score=60,
                    citation_score=50,
                    coverage_score=80,
                    confidence_score=90,
                    visibility_score=65,
                    version="1.0",
                ),
                ResearchScore(
                    research_id=current.id,
                    mention_score=75,
                    recommendation_score=72,
                    citation_score=58,
                    coverage_score=77,
                    confidence_score=92,
                    visibility_score=74,
                    version="1.0",
                ),
            ]
        )
        db.commit()
        current_id = current.id
        previous_id = previous.id

    detected = client.post(f"/research/{current_id}/changes")
    assert detected.status_code == 200
    result = detected.json()
    assert result["previous_research_id"] == previous_id
    assert result["metric_deltas"] == {
        "visibility_score": 9.0,
        "recommendation_score": 12.0,
        "citation_score": 8.0,
        "coverage_score": -3.0,
    }
    assert result["graph_changes"] == {
        "added_nodes": [],
        "removed_nodes": [],
        "added_edges": [],
        "removed_edges": [],
    }
    assert client.get(f"/research/{current_id}/changes").json()["id"] == result["id"]


def test_notification_center_ui_email_telegram_outbox(client: TestClient) -> None:
    created = client.post(
        "/notifications/events",
        json={
            "event_type": "PROVIDER_UNAVAILABLE",
            "title": "Gemini недоступен",
            "message": "Router переключился на резервного провайдера",
            "resource_type": "provider",
            "resource_id": "gemini",
            "channels": ["UI", "EMAIL", "TELEGRAM"],
        },
    )
    assert created.status_code == 201
    item = created.json()
    states = {delivery["channel"]: delivery["status"] for delivery in item["deliveries"]}
    assert states == {"UI": "DELIVERED", "EMAIL": "PENDING", "TELEGRAM": "PENDING"}
    assert client.get("/notifications", params={"unread_only": True}).json()[0][
        "id"
    ] == item["id"]
    read = client.post(f"/notifications/{item['id']}/read")
    assert read.status_code == 200
    assert read.json()["is_read"] is True
    assert client.get("/notifications", params={"unread_only": True}).json() == []
    invalid = client.post(
        "/notifications/events",
        json={
            "event_type": "EXECUTION_FAILED",
            "title": "Failure",
            "message": "Execution failed",
            "channels": ["SMS"],
        },
    )
    assert invalid.status_code == 422


def test_closed_beta_invitation_access_limits_search_and_audit(client: TestClient) -> None:
    created = client.post(
        "/admin/beta/invitations",
        json={"email": "analyst@example.com", "expires_in_hours": 24},
    )
    assert created.status_code == 201
    invitation = created.json()
    resent = client.post(
        f"/admin/beta/invitations/{invitation['id']}/resend"
    )
    assert resent.status_code == 200
    assert resent.json()["send_count"] == 2
    assert resent.json()["token"] != invitation["token"]
    assert client.post(
        f"/beta/invitations/{invitation['token']}/accept",
        json={"display_name": "Old token", "password": "strong-password"},
    ).status_code == 404

    accepted = client.post(
        f"/beta/invitations/{resent.json()['token']}/accept",
        json={"display_name": "Beta Analyst", "password": "strong-password"},
    )
    assert accepted.status_code == 200
    user_id = accepted.json()["user_id"]
    assert accepted.json()["status"] == "ACTIVE"
    assert client.post(
        f"/beta/invitations/{resent.json()['token']}/accept",
        json={"display_name": "Again", "password": "strong-password"},
    ).status_code == 404

    users = client.get(
        "/admin/beta/users", params={"search": "analyst", "status": "ACTIVE"}
    )
    assert users.status_code == 200
    assert users.json()[0]["last_seen_at"] is None
    updated = client.patch(
        f"/admin/beta/users/{user_id}",
        json={
            "status": "SUSPENDED",
            "limits": {
                "daily_research_limit": 2,
                "monthly_research_limit": 20,
                "max_projects": 3,
                "max_domains": 6,
                "max_organization_users": 2,
            },
        },
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "SUSPENDED"
    assert updated.json()["limits"]["max_projects"] == 3
    audit = client.get(
        "/audit/events", params={"category": "closed_beta"}
    ).json()
    assert audit["total"] >= 4

    revoked = client.post(
        "/admin/beta/invitations",
        json={"email": "revoked@example.com"},
    ).json()
    assert client.post(
        f"/admin/beta/invitations/{revoked['id']}/revoke"
    ).status_code == 200
    assert client.post(
        f"/beta/invitations/{revoked['token']}/accept",
        json={"display_name": "Revoked", "password": "strong-password"},
    ).status_code == 404
