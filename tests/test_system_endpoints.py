from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_returns_configured_version() -> None:
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"version": "1.0.0-rc2.1"}
