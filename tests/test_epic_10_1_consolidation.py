from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from research.models import ResearchJobState
from research.queue import process_next

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


def test_llm_domains_have_no_provider_factory_bypass() -> None:
    for path in (
        Path("research/service.py"),
        Path("product/service.py"),
        Path("model_benchmark/service.py"),
        Path("model_evaluation/service.py"),
    ):
        source = path.read_text(encoding="utf-8")
        assert "ProviderFactory" not in source
        assert "providers.factory" not in source


def test_profiles_are_the_public_user_routing_contract(client: TestClient) -> None:
    profiles = client.get("/router/profiles")
    assert profiles.status_code == 200
    assert {item["profile"] for item in profiles.json()} == {
        "FAST",
        "BALANCED",
        "HIGH_QUALITY",
        "FREE",
        "PRIVATE",
        "ENTERPRISE",
    }


def test_hard_budget_rejects_plan_when_no_affordable_model_exists(
    client: TestClient,
) -> None:
    updated = client.patch(
        "/router/policies/quality-first",
        json={"daily_budget_usd": 0.00000001},
    )
    assert updated.status_code == 200
    response = client.post(
        "/router/route",
        json={
            "query": "premium analysis",
            "policy_id": "quality-first",
            "allowed_models": ["claude-3-5-sonnet"],
            "context_tokens": 10_000,
            "max_output_tokens": 2_000,
        },
    )
    assert response.status_code == 409
    assert "Hard budget exceeded" in response.json()["detail"]


def test_async_research_queue_returns_before_worker_processing(client: TestClient) -> None:
    assert client.post("/agents", json={"name": "async-router-agent"}).status_code == 201
    research = client.post("/research", json={"title": "Queued routing profile"}).json()
    queued = client.post(
        "/research/run",
        json={
            "research_id": research["id"],
            "routing_profile": "BALANCED",
            "query": "Analyze Skinjestique",
        },
    )
    assert queued.status_code == 202
    assert queued.json()["state"] == "PENDING"
    job_status = client.get(f"/research/jobs/{queued.json()['id']}")
    assert job_status.status_code == 200
    assert job_status.json()["state"] == "PENDING"
    with TestingSession() as db:
        completed = process_next(db)
        assert completed is not None
        assert completed.state == ResearchJobState.COMPLETED
