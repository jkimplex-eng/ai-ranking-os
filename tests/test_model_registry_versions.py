from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app

engine = create_engine(
    "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
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


def test_model_registry_preserves_version_history(client: TestClient) -> None:
    created = client.post(
        "/router/models",
        json={
            "id": "test-model", "provider": "openai", "display_name": "Test Model",
            "version": "2026-01", "status": "ACTIVE", "tier": "STANDARD",
            "capabilities": ["chat", "json"],
            "pricing": {"input_per_million": 1, "output_per_million": 2},
            "latency_ms": 100, "tokens_per_second": 50, "average_latency": 100,
            "benchmark_score": 82, "quality": 0.8, "availability": 0.99,
            "context_window": 128000, "hallucination_rate": 0.1,
            "reasoning": True, "json_mode": True, "tool_calling": True,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["version"] == "2026-01"
    updated = client.patch("/router/models/test-model", json={"version": "2026-02"})
    assert updated.status_code == 200
    versions = client.get("/router/model/test-model/versions")
    assert versions.status_code == 200
    assert [item["version"] for item in versions.json()] == ["2026-02", "2026-01"]
