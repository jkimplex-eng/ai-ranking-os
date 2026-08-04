from pathlib import Path

from backend.app.config import Settings
from hardening.validation import validate_startup


def test_container_has_healthcheck_and_exec_entrypoint() -> None:
    dockerfile = Path("Dockerfile").read_text()
    entrypoint = Path("infra/docker/entrypoint.sh").read_text()
    assert "HEALTHCHECK" in dockerfile
    assert 'ENTRYPOINT ["/app/infra/docker/entrypoint.sh"]' in dockerfile
    assert "exec uvicorn" in entrypoint
    assert "--timeout-graceful-shutdown" in entrypoint


def test_kubernetes_uses_one_worker_per_pod_and_probes() -> None:
    manifest = Path("infra/kubernetes/api.yaml").read_text()
    assert 'value: "1"' in manifest
    assert "readinessProbe:" in manifest
    assert "livenessProbe:" in manifest
    assert "terminationGracePeriodSeconds: 40" in manifest


def test_production_startup_rejects_default_jwt_secret() -> None:
    settings = Settings(
        app_env="production",
        database_url="postgresql+psycopg://user:pass@db/app",
        redis_url="redis://redis:6379/0",
    )
    assert "AUTH_JWT_SECRET must be replaced in production" in validate_startup(settings)
