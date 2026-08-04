import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import app
from hardening.service import (
    BackpressureError,
    BackpressureGate,
    CircuitBreaker,
    CircuitOpenError,
    RetryPolicy,
)
from hardening.validation import validate_startup


def test_circuit_retry_backpressure():
    breaker = CircuitBreaker(failure_threshold=1, recovery_seconds=60)
    with pytest.raises(ValueError):
        breaker.execute(lambda: (_ for _ in ()).throw(ValueError()))
    with pytest.raises(CircuitOpenError):
        breaker.execute(lambda: 1)
    calls = []

    def flaky():
        calls.append(1)
        return "ok" if len(calls) == 3 else (_ for _ in ()).throw(ValueError())

    assert RetryPolicy(attempts=3, base_delay_seconds=0).execute(flaky) == "ok"
    gate = BackpressureGate(1)
    gate.enter()
    with pytest.raises(BackpressureError):
        gate.enter()
    gate.leave()


def test_startup_and_api():
    assert validate_startup(
        Settings(app_env="production", database_url="sqlite://", redis_url="redis://x")
    )
    client = TestClient(app)
    assert client.get("/hardening/status").json()["status"] == "ready"
    assert "/hardening/dlq" in app.openapi()["paths"]
