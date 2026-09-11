from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.providers.base import GenerateRequest
from backend.app.providers.cache import TTLCache
from backend.app.providers.capabilities import Region
from backend.app.providers.credentials import CredentialManager
from backend.app.providers.exceptions import ProviderError, ProviderErrorCategory
from backend.app.providers.factory import factory
from backend.app.providers.models import ProviderUsageRecord
from backend.app.providers.provider import ConfiguredProvider
from backend.app.providers.rate_limit import ProviderRateLimiter, RateLimitPolicy
from backend.app.providers.registry import registry

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


def test_all_global_and_russian_providers_implement_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROVIDER_MOCK_MODE", "true")
    providers = {provider.name: provider for provider in factory.all()}
    assert set(providers) == {
        "openai",
        "openrouter",
        "anthropic",
        "gemini",
        "deepseek",
        "perplexity",
        "mistral",
        "grok",
        "ollama",
        "groq",
        "github",
        "yandex",
        "gigachat",
    }
    assert providers["yandex"].region == Region.RUSSIA
    assert providers["gigachat"].region == Region.RUSSIA
    assert providers["openai"].region == Region.GLOBAL

    for provider in providers.values():
        model = provider.models()[0]
        response = provider.generate(
            GenerateRequest(model=model.id, prompt="contract smoke")
        )
        assert response.provider == provider.name
        assert response.usage.total_tokens > 0
        assert response.usage.estimated_cost >= 0
        assert provider.health()["available"] is True
        assert provider.estimate_tokens("hello") > 0
        assert isinstance(provider.capabilities(model.id).context_window, int)
        assert isinstance(provider.supports_streaming(model.id), bool)
        assert isinstance(provider.supports_function_calling(model.id), bool)
        assert isinstance(provider.supports_json_mode(model.id), bool)


def test_streaming_and_response_cache() -> None:
    provider = factory.create("openai")
    request = GenerateRequest(model="gpt-4o-mini", prompt="one two three")
    assert list(provider.stream(request)) == ["one", "two", "three"]
    first = provider.generate(request)
    second = provider.generate(request)
    assert first.cached is False
    assert second.cached is True
    assert second.content == first.content


def test_embeddings_and_unsupported_capability() -> None:
    openai = factory.create("openai")
    embedded = openai.embed(
        ["alpha", "beta"],
        model="text-embedding-3-small",
    )
    assert len(embedded.vectors) == 2

    yandex = factory.create("yandex")
    with pytest.raises(ProviderError) as caught:
        yandex.embed(["alpha"])
    assert caught.value.category == ProviderErrorCategory.UNSUPPORTED_CAPABILITY


def test_hot_credentials_from_override_env_and_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = CredentialManager(
        docker_secrets_dir=tmp_path,
        kubernetes_secrets_dir=tmp_path / "k8s",
    )
    monkeypatch.setenv("TEST_PROVIDER_KEY", "env-value")
    assert manager.get("TEST_PROVIDER_KEY") == "env-value"
    manager.set("TEST_PROVIDER_KEY", "hot-value")
    assert manager.get("TEST_PROVIDER_KEY") == "hot-value"
    manager.clear("TEST_PROVIDER_KEY")
    assert manager.get("TEST_PROVIDER_KEY") == "env-value"
    monkeypatch.delenv("TEST_PROVIDER_KEY")
    (tmp_path / "TEST_PROVIDER_KEY").write_text("secret-value", encoding="utf-8")
    assert manager.get("TEST_PROVIDER_KEY") == "secret-value"


def test_rate_limiter_enforces_rpm_and_releases_concurrency() -> None:
    limiter = ProviderRateLimiter(
        "test",
        RateLimitPolicy(rpm=1, tpm=100, concurrent_requests=1, retry_budget=1),
    )
    limiter.acquire(10)
    limiter.release()
    with pytest.raises(ProviderError) as caught:
        limiter.acquire(10)
    assert caught.value.category == ProviderErrorCategory.RATE_LIMIT


def test_ttl_cache_namespaces_and_expiry() -> None:
    cache = TTLCache(ttl_seconds=10, max_entries=2)
    key = cache.key("response", "provider", "prompt")
    cache.set(key, {"answer": 42})
    assert cache.get(key) == {"answer": 42}
    cache.set("expired", "value", ttl_seconds=-1)
    assert cache.get("expired") is None


@pytest.mark.parametrize(
    ("region", "providers"),
    [
        ("RUSSIA", {"yandex", "gigachat"}),
        (
            "GLOBAL",
            {
                "openai",
                "anthropic",
                "gemini",
                "deepseek",
                "perplexity",
                "mistral",
                "grok",
                "ollama",
                "groq",
                "github",
            },
        ),
    ],
)
def test_router_respects_region(
    client: TestClient,
    region: str,
    providers: set[str],
) -> None:
    response = client.post(
        "/router/route",
        json={
            "query": "Сравни модели",
            "region": region,
            "language": "ru",
            "policy_id": "quality-first",
        },
    )
    assert response.status_code == 201, response.text
    assert {score["provider"] for score in response.json()["scores"]} <= providers


def test_parallel_provider_execution_persists_usage(client: TestClient) -> None:
    response = client.post(
        "/executor/run",
        json={
            "plan_id": "multi-provider",
            "mode": "PARALLEL",
            "steps": [
                {
                    "step_id": "global",
                    "provider": "openai",
                    "payload": {"model": "gpt-4o-mini", "query": "hello"},
                },
                {
                    "step_id": "russia",
                    "provider": "yandex",
                    "payload": {"model": "yandexgpt-pro", "query": "привет"},
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["state"] == "COMPLETED"
    with TestingSession() as db:
        usage = list(db.scalars(select(ProviderUsageRecord)))
        assert {record.provider for record in usage} == {"openai", "yandex"}


def test_consensus_mode_executes_all_providers(client: TestClient) -> None:
    response = client.post(
        "/executor/run",
        json={
            "plan_id": "consensus",
            "mode": "CONSENSUS",
            "steps": [
                {
                    "step_id": "one",
                    "provider": "openai",
                    "payload": {"model": "gpt-4o-mini", "query": "same"},
                },
                {
                    "step_id": "two",
                    "provider": "deepseek",
                    "payload": {"model": "deepseek-chat", "query": "same"},
                },
            ],
        },
    )
    assert response.status_code == 201
    assert len(response.json()["results"]) == 2
    assert "consensus" in response.json()["output"]


class FakeTransport:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[tuple[str, str, dict]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict | None = None,
    ) -> dict:
        self.calls.append((method, url, {"headers": headers, "json": json}))
        return self.payload


@pytest.mark.parametrize(
    ("provider_name", "response_payload", "expected"),
    [
        (
            "openai",
            {
                "choices": [
                    {"message": {"content": "openai-live"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            },
            "openai-live",
        ),
        (
            "anthropic",
            {
                "content": [{"type": "text", "text": "anthropic-live"}],
                "usage": {"input_tokens": 3, "output_tokens": 2},
                "stop_reason": "end_turn",
            },
            "anthropic-live",
        ),
        (
            "gemini",
            {
                "candidates": [
                    {
                        "content": {"parts": [{"text": "gemini-live"}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 3,
                    "candidatesTokenCount": 2,
                },
            },
            "gemini-live",
        ),
        (
            "yandex",
            {
                "result": {
                    "alternatives": [
                        {
                            "message": {"text": "yandex-live"},
                            "status": "FINAL",
                        }
                    ],
                    "usage": {"inputTextTokens": 3, "completionTokens": 2},
                }
            },
            "yandex-live",
        ),
    ],
)
def test_live_transport_contracts_without_external_network(
    monkeypatch: pytest.MonkeyPatch,
    provider_name: str,
    response_payload: dict,
    expected: str,
) -> None:
    monkeypatch.setenv("PROVIDER_MOCK_MODE", "false")
    for name in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "YANDEX_API_KEY",
        "YANDEX_FOLDER_ID",
    ):
        monkeypatch.setenv(name, "test-secret")
    transport = FakeTransport(response_payload)
    provider = ConfiguredProvider(
        registry.get(provider_name),
        transport=transport,  # type: ignore[arg-type]
    )
    model = next(
        item for item in provider.models() if item.capabilities.supports("chat")
    )
    response = provider.generate(
        GenerateRequest(model=model.id, prompt="live contract")
    )
    assert response.content == expected
    assert response.usage.prompt_tokens == 3
    assert response.usage.completion_tokens == 2
    assert transport.calls
