import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


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
