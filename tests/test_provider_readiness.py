import httpx
import pytest

from backend.app.providers.base import GenerateRequest
from backend.app.providers.cache import provider_cache
from backend.app.providers.credentials import credentials
from backend.app.providers.exceptions import ProviderError
from backend.app.providers.factory import factory
from backend.app.providers.transport import HTTPTransport

EXPECTED_PROVIDERS = {
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
    "yandex",
    "gigachat",
}


def test_provider_contract_matrix() -> None:
    providers = {provider.name: provider for provider in factory.all()}
    assert providers.keys() >= EXPECTED_PROVIDERS
    for name in EXPECTED_PROVIDERS:
        provider = providers[name]
        assert provider.health()["available"] is True
        chat_model = next(
            model for model in provider.models() if model.capabilities.supports("chat")
        )
        response = provider.generate(
            GenerateRequest(
                model=chat_model.id,
                prompt="Analyze Skinjestique",
                metadata={"target_entity": "Skinjestique"},
            )
        )
        assert response.provider == name
        assert response.usage.total_tokens > 0
        assert response.usage.estimated_cost >= 0
        if chat_model.capabilities.supports("citations"):
            assert response.citations
        if provider.supports_streaming(chat_model.id):
            assert list(provider.stream(GenerateRequest(model=chat_model.id, prompt="hello")))


def test_transport_retries_retryable_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def request(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise httpx.ConnectError("temporary")
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", "https://x"))

    monkeypatch.setattr(httpx, "request", request)
    transport = HTTPTransport(max_retries=3, retry_base_seconds=0)
    assert transport.request("GET", "https://x", headers={}) == {"ok": True}
    assert attempts == 3


def test_transport_does_not_retry_authentication(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def request(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        return httpx.Response(401, request=httpx.Request("GET", "https://x"))

    monkeypatch.setattr(httpx, "request", request)
    with pytest.raises(ProviderError):
        HTTPTransport(max_retries=3, retry_base_seconds=0).request("GET", "https://x", headers={})
    assert attempts == 1


def test_yandex_health_uses_completion_endpoint_and_native_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROVIDER_MOCK_MODE", "false")
    credentials.set("YANDEX_API_KEY", "test-key")
    credentials.set("YANDEX_FOLDER_ID", "test-folder")
    provider_cache._values.clear()
    provider = factory.create("yandex")
    captured: dict[str, object] = {}

    def request(method: str, url: str, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return {
            "result": {
                "alternatives": [
                    {"message": {"role": "assistant", "text": "ok"}, "status": "FINAL"}
                ],
                "usage": {"inputTextTokens": "1", "completionTokens": "1"},
            }
        }

    monkeypatch.setattr(provider._transport, "request", request)
    try:
        assert provider.health()["available"] is True
        assert captured["method"] == "POST"
        assert str(captured["url"]).endswith("/completion")
        payload = captured["json"]
        assert payload["modelUri"] == "gpt://test-folder/yandexgpt/latest"
        assert payload["messages"] == [{"role": "user", "text": "ping"}]
    finally:
        credentials.clear("YANDEX_API_KEY")
        credentials.clear("YANDEX_FOLDER_ID")
        provider_cache._values.clear()
