from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.llm_router.circuit_breaker import (
    allow_request,
    record_failure,
    record_success,
)
from backend.app.llm_router.models import CircuitBreakerRecord
from backend.app.main import app
from providers import PROVIDER_CLASSES, ProviderRequest, create_provider

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture
def client() -> Generator[TestClient]:
    Base.metadata.create_all(test_engine)

    def override_get_db() -> Generator[Session]:
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)


def test_registry_crud_filtering_and_pagination(client: TestClient) -> None:
    seeded = client.get("/router/models", params={"page_size": 3})
    assert seeded.status_code == 200
    assert seeded.json()["total"] == 10
    assert len(seeded.json()["items"]) == 3

    capable = client.get("/router/models", params={"capability": "research"})
    assert capable.status_code == 200
    assert capable.json()["total"] == 3
    assert all("research" in item["capabilities"] for item in capable.json()["items"])

    payload = {
        "id": "custom-rc1",
        "provider": "local",
        "display_name": "Custom RC1",
        "tier": "LOCAL",
        "capabilities": ["chat", "json"],
        "pricing": {"input_per_million": 0, "output_per_million": 0},
        "latency_ms": 100,
        "quality": 0.75,
        "availability": 0.99,
        "context_window": 8192,
        "hallucination_rate": 0.1,
        "domains": ["general"],
        "languages": ["en"],
    }
    assert client.post("/router/models", json=payload).status_code == 201
    updated = client.patch(
        "/router/models/custom-rc1",
        json={"status": "MAINTENANCE", "quality": 0.8},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "MAINTENANCE"
    assert updated.json()["quality"] == 0.8
    assert client.get("/router/model/custom-rc1").status_code == 200
    assert client.delete("/router/models/custom-rc1").status_code == 204
    assert client.get("/router/model/custom-rc1").status_code == 404


@pytest.mark.parametrize(
    ("policy_id", "expected_mode"),
    [
        ("quality-first", "SINGLE"),
        ("cost-optimized", "FALLBACK"),
        ("latency-critical", "FALLBACK"),
        ("research-grade", "ENSEMBLE"),
        ("multilingual", "PARALLEL"),
    ],
)
def test_router_policies_build_executable_plans(
    client: TestClient,
    policy_id: str,
    expected_mode: str,
) -> None:
    response = client.post(
        "/router/route",
        json={
            "query": "Сравни модели и приведи источники",
            "policy_id": policy_id,
            "language": "ru",
            "context_tokens": 1000,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["plan"]["mode"] == expected_mode
    assert body["selected_models"]
    assert set(body["scores"][0]["factors"]) == {
        "intent",
        "cost",
        "latency",
        "quality",
        "context",
        "hallucination",
        "domain",
        "language",
        "region",
        "success",
    }
    assert body["router_latency_ms"] >= 0


def test_router_history_status_policy_update_and_openapi(client: TestClient) -> None:
    assert client.post("/router/plan", json={"query": "hello"}).status_code == 201
    history = client.get("/router/history")
    assert history.status_code == 200
    assert history.json()["total"] == 1

    policies = client.get("/router/policies")
    assert policies.status_code == 200
    assert len(policies.json()) == 5
    updated = client.patch(
        "/router/policies/quality-first",
        json={"daily_budget_usd": 25, "top_k": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["daily_budget_usd"] == 25

    status = client.get("/router/status")
    assert status.status_code == 200
    assert status.json()["models"]["ACTIVE"] == 10
    paths = client.get("/openapi.json").json()["paths"]
    for path in (
        "/router/route",
        "/router/models",
        "/system/health",
        "/system/metrics",
        "/metrics",
    ):
        assert path in paths


def test_router_automatically_downgrades_when_budget_is_exhausted(
    client: TestClient,
) -> None:
    assert (
        client.patch(
            "/router/policies/quality-first",
            json={"daily_budget_usd": 0.00000001},
        ).status_code
        == 200
    )
    response = client.post(
        "/router/route",
        json={
            "query": "Produce a detailed research answer",
            "policy_id": "quality-first",
            "context_tokens": 10_000,
            "max_output_tokens": 2_000,
        },
    )
    assert response.status_code == 201
    assert response.json()["budget_downgraded"] is True


def test_circuit_breaker_full_state_machine(client: TestClient) -> None:
    client.get("/router/models")
    with TestingSession() as db:
        for _ in range(3):
            record_failure(db, "gpt-4o-mini")
        record = db.get(CircuitBreakerRecord, "gpt-4o-mini")
        assert record is not None
        assert record.state == "OPEN"
        assert not allow_request(db, "gpt-4o-mini")

        record.opened_at = datetime.now(UTC) - timedelta(seconds=61)
        db.commit()
        assert allow_request(db, "gpt-4o-mini")
        assert record.state == "HALF_OPEN"
        record_success(db, "gpt-4o-mini")
        record_success(db, "gpt-4o-mini")
        assert record.state == "CLOSED"


def test_all_provider_interfaces_are_execution_ready() -> None:
    assert set(PROVIDER_CLASSES) == {
        "openai",
        "anthropic",
        "gemini",
        "deepseek",
        "perplexity",
        "mistral",
        "grok",
        "local",
    }
    for provider_name in PROVIDER_CLASSES:
        provider = create_provider(provider_name)
        assert provider.health()["status"] == "available"
        response = provider.complete(
            ProviderRequest(model=f"{provider_name}-model", prompt="hello")
        )
        assert response.provider == provider_name
        assert response.mock is True
        assert response.output_tokens > 0


@pytest.mark.parametrize(
    "path",
    [
        "/system/health",
        "/system/status",
        "/system/providers",
        "/system/router",
        "/system/pipeline",
        "/system/metrics",
        "/system/version",
        "/system/costs",
        "/system/cache",
        "/system/build",
    ],
)
def test_system_monitoring_endpoints(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200, response.text


def test_prometheus_endpoint_is_scrape_compatible(client: TestClient) -> None:
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "ai_ranking_os_http_requests_total" in response.text
    assert "ai_ranking_os_router_latency_seconds" in response.text
