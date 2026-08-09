from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from provider_registry.repository import ProviderRepository
from provider_registry.schemas import ProviderCreate
from provider_registry.service import ProviderRegistryService

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


def test_registry_seeds_all_required_providers(client: TestClient) -> None:
    response = client.get("/providers")
    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {
        "openai", "anthropic", "google", "groq", "openrouter", "github",
        "cloudflare", "huggingface", "nvidia", "ollama", "deepseek", "qwen",
        "mistral", "yandexgpt", "gigachat",
    }
    detail = client.get("/providers/ollama")
    assert detail.status_code == 200
    assert detail.json()["free_tier"] is True


def test_capability_matrix_and_extensible_repository(client: TestClient) -> None:
    matrix = client.get("/providers/capabilities")
    assert matrix.status_code == 200
    assert "ollama" in matrix.json()["capabilities"]["embeddings"]
    with TestingSession() as db:
        service = ProviderRegistryService(ProviderRepository(db))
        service.ensure_seeded()
        created = service.repository.create(
            ProviderCreate(
                id="custom", display_name="Custom", context_window=4096,
                capabilities=["chat"], free_tier=True,
            )
        )
        assert created.id == "custom"
