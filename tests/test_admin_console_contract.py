from fastapi.testclient import TestClient

from backend.app.main import app


def test_admin_console_public_contracts_are_available() -> None:
    paths = app.openapi()["paths"]
    required = {
        "/admin/beta/users",
        "/organizations",
        "/research",
        "/reports",
        "/providers",
        "/execution/history",
        "/admin/feedback",
        "/product-analytics/dashboard",
        "/audit/events",
        "/system/health",
        "/workspace",
    }

    assert required <= paths.keys()


def test_admin_console_health_is_read_only() -> None:
    client = TestClient(app)
    response = client.get("/system/health")

    assert response.status_code == 200
    assert response.json()["status"] in {"healthy", "degraded", "unhealthy"}
    assert {"database", "cache"} <= response.json().keys()
