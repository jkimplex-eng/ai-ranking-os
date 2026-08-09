import json
from collections.abc import Iterator

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.providers.base import GenerateRequest
from backend.app.providers.ollama import OllamaProvider


class FakeOllamaTransport:
    def request(self, method: str, url: str, *, headers: dict, json: dict | None = None) -> dict:
        if url.endswith("/api/tags"):
            return {
                "models": [
                    {
                        "name": "qwen3:8b",
                        "size": 5_000_000_000,
                        "digest": "abc",
                        "details": {"family": "qwen3", "parameter_size": "8B"},
                    }
                ]
            }
        if url.endswith("/api/show"):
            return {
                "capabilities": ["completion", "tools", "thinking", "vision"],
                "model_info": {"qwen3.context_length": 32768},
            }
        if url.endswith("/api/chat"):
            return {
                "message": {"content": "hello"},
                "prompt_eval_count": 4,
                "eval_count": 2,
                "done_reason": "stop",
            }
        raise AssertionError(url)

    def stream(
        self, method: str, url: str, *, headers: dict, json: dict
    ) -> Iterator[str]:
        yield json_module.dumps({"message": {"content": "one"}})
        yield json_module.dumps({"message": {"content": " two"}, "done": True})


json_module = json


def test_native_ollama_discovery_generate_and_stream() -> None:
    provider = OllamaProvider(transport=FakeOllamaTransport(), mock_mode=False)  # type: ignore[arg-type]
    models = provider.discover_models()
    assert models[0].context_length == 32768
    assert models[0].vision is True
    assert models[0].reasoning is True
    assert models[0].tools is True
    response = provider.generate(GenerateRequest(model="qwen3:8b", prompt="hello"))
    assert response.content == "hello"
    assert response.usage.total_tokens == 6
    assert list(provider.stream(GenerateRequest(model="qwen3:8b", prompt="hello"))) == [
        "one",
        " two",
    ]


def test_ollama_models_health_api() -> None:
    with TestClient(app) as client:
        models = client.get("/providers/ollama/models")
        health = client.get("/providers/ollama/health")
    assert models.status_code == 200
    assert {item["name"] for item in models.json()} >= {
        "llama3.2:latest",
        "nomic-embed-text:latest",
    }
    assert health.status_code == 200
    assert health.json()["available"] is True
