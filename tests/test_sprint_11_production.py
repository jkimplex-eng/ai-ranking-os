import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from deployment.production.scripts import smoke_test


def test_live_ready_and_request_id(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    with TestClient(app) as client:
        live = client.get("/live", headers={"X-Request-ID": "sprint-11-test"})
        assert live.status_code == 200
        assert live.headers["X-Request-ID"] == "sprint-11-test"
        assert live.json() == {"status": "alive"}


def test_production_assets_define_isolated_services() -> None:
    compose = Path("deployment/production/docker-compose.yml").read_text(encoding="utf-8")
    for service in ("postgres:", "redis:", "backend:", "worker:", "frontend:", "nginx:"):
        assert service in compose
    assert "127.0.0.1:${EDGE_PORT:-8100}:8080" in compose
    assert "unless-stopped" in compose


def test_smoke_script_is_valid_python() -> None:
    source = Path("deployment/production/scripts/smoke_test.py").read_text(encoding="utf-8")
    compile(source, "smoke_test.py", "exec")
    assert json.loads('{"status":"PASS"}')["status"] == "PASS"


def test_smoke_waits_for_asynchronous_research(monkeypatch) -> None:
    states = iter(["ACTIVE", "ACTIVE", "COMPLETED"])
    calls = []

    def fake_call(path, *, token):
        calls.append((path, token))
        return 200, {"status": next(states)}

    monkeypatch.setattr(smoke_test, "call", fake_call)
    monkeypatch.setattr(smoke_test.time, "sleep", lambda seconds: None)

    assert smoke_test.wait_for_research(42, "test-token") == {"status": "COMPLETED"}
    assert calls == [("/api/research/42", "test-token")] * 3


def test_invitation_secrets_are_not_sent_or_logged_in_request_urls() -> None:
    client = Path("frontend/src/api.ts").read_text(encoding="utf-8")
    edge = Path("deployment/production/nginx/internal.conf").read_text(encoding="utf-8")
    host = Path("deployment/production/nginx/host-vhost.conf.example").read_text(
        encoding="utf-8"
    )

    assert '"/beta/invitations/accept"' in client
    assert "`/beta/invitations/${" not in client
    for config in (edge, host):
        assert "location ^~ /api/beta/invitations/ {" in config
        assert "access_log off;" in config
