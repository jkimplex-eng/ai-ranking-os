import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.app.providers.base import (
    EmbeddingResponse,
    GenerateRequest,
    GenerateResponse,
    Provider,
    ProviderModel,
)
from backend.app.providers.capabilities import Capability, ModelCapabilities, Region
from backend.app.providers.exceptions import ProviderError, ProviderErrorCategory
from backend.app.providers.pricing import ModelPrice
from backend.app.providers.transport import HTTPTransport


class OllamaModelInfo(BaseModel):
    name: str
    size: int = Field(default=0, ge=0)
    digest: str = ""
    modified_at: datetime | None = None
    family: str | None = None
    parameter_size: str | None = None
    quantization_level: str | None = None
    context_length: int = Field(default=4096, gt=0)
    embedding: bool = False
    vision: bool = False
    reasoning: bool = False
    tools: bool = False
    json_mode: bool = True
    streaming: bool = True


class OllamaProvider(Provider):
    """Native Ollama adapter implementing the platform Provider port."""

    name = "ollama"
    region = Region.GLOBAL

    def __init__(
        self,
        *,
        base_url: str | None = None,
        transport: HTTPTransport | None = None,
        mock_mode: bool | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip(
            "/"
        )
        self._transport = transport or HTTPTransport(
            float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60")), max_retries=2
        )
        configured_mock = os.getenv("OLLAMA_MOCK_MODE")
        self.mock_mode = (
            mock_mode
            if mock_mode is not None
            else configured_mock.casefold() not in {"false", "0", "no"}
            if configured_mock is not None
            else os.getenv("PROVIDER_MOCK_MODE", "true").casefold() not in {"false", "0", "no"}
        )
        self._discovered: list[OllamaModelInfo] | None = None

    def discover_models(self, *, refresh: bool = False) -> list[OllamaModelInfo]:
        if self._discovered is not None and not refresh:
            return list(self._discovered)
        if self.mock_mode:
            self._discovered = [
                OllamaModelInfo(
                    name="qwen2.5:3b",
                    size=1_900_000_000,
                    family="qwen2",
                    parameter_size="3B",
                    quantization_level="Q4_K_M",
                    context_length=32768,
                    tools=True,
                    reasoning=True,
                ),
                OllamaModelInfo(
                    name="llama3.2:latest",
                    size=2_000_000_000,
                    family="llama",
                    parameter_size="3B",
                    quantization_level="Q4_K_M",
                    context_length=131072,
                    tools=True,
                    reasoning=True,
                ),
                OllamaModelInfo(
                    name="nomic-embed-text:latest",
                    size=274_000_000,
                    family="nomic-bert",
                    parameter_size="137M",
                    context_length=8192,
                    embedding=True,
                    json_mode=False,
                    tools=False,
                ),
            ]
            return list(self._discovered)
        tags = self._transport.request("GET", f"{self.base_url}/api/tags", headers={})
        discovered: list[OllamaModelInfo] = []
        for raw in tags.get("models", []):
            name = str(raw.get("name") or raw.get("model") or "")
            if not name:
                continue
            details = self._transport.request(
                "POST", f"{self.base_url}/api/show", headers={}, json={"model": name}
            )
            capabilities = {str(value).casefold() for value in details.get("capabilities", [])}
            model_info = details.get("model_info", {})
            context_length = next(
                (
                    int(value)
                    for key, value in model_info.items()
                    if key.endswith(".context_length") and isinstance(value, int | float)
                ),
                4096,
            )
            metadata = raw.get("details", {})
            family = str(metadata.get("family") or model_info.get("general.architecture") or "")
            discovered.append(
                OllamaModelInfo(
                    name=name,
                    size=int(raw.get("size", 0)),
                    digest=str(raw.get("digest", "")),
                    modified_at=raw.get("modified_at"),
                    family=family or None,
                    parameter_size=metadata.get("parameter_size"),
                    quantization_level=metadata.get("quantization_level"),
                    context_length=context_length,
                    embedding="embedding" in capabilities,
                    vision="vision" in capabilities or "clip" in family.casefold(),
                    reasoning="thinking" in capabilities or "reason" in name.casefold(),
                    tools="tools" in capabilities,
                    json_mode="completion" in capabilities,
                    streaming="completion" in capabilities,
                )
            )
        self._discovered = discovered
        return list(discovered)

    def models(self) -> list[ProviderModel]:
        return [
            ProviderModel(
                id=item.name,
                region=self.region,
                capabilities=ModelCapabilities(
                    context_window=item.context_length,
                    max_output_tokens=min(32768, item.context_length),
                    features={
                        Capability.CHAT,
                        *({Capability.STREAMING} if item.streaming else set()),
                        *({Capability.JSON_MODE} if item.json_mode else set()),
                        *({Capability.EMBEDDINGS} if item.embedding else set()),
                        *({Capability.VISION} if item.vision else set()),
                        *(
                            {Capability.FUNCTION_CALLING, Capability.TOOL_USE}
                            if item.tools
                            else set()
                        ),
                    },
                ),
                price=ModelPrice(
                    provider=self.name,
                    model=item.name,
                    input_per_million=0,
                    output_per_million=0,
                ),
            )
            for item in self.discover_models()
        ]

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        self._model(request.model)
        if request.json_mode and not self.supports_json_mode(request.model):
            raise self._unsupported("json_mode")
        if request.tools and not self.supports_function_calling(request.model):
            raise self._unsupported("function_calling")
        if self.mock_mode:
            content = (
                json.dumps({"response": request.text()})
                if request.json_mode
                else request.text()
            )
            prompt_tokens = self.estimate_tokens(request.text())
            completion_tokens = self.estimate_tokens(content)
            raw: dict[str, Any] = {"mock": True}
            finish_reason = "stop"
        else:
            payload = self._chat_payload(request, stream=False)
            raw = self._transport.request(
                "POST", f"{self.base_url}/api/chat", headers={}, json=payload
            )
            content = str(raw.get("message", {}).get("content", ""))
            prompt_tokens = int(raw.get("prompt_eval_count", 0)) or self.estimate_tokens(
                request.text()
            )
            completion_tokens = int(raw.get("eval_count", 0)) or self.estimate_tokens(content)
            finish_reason = str(raw.get("done_reason", "stop"))
        return GenerateResponse(
            provider=self.name,
            model=request.model,
            content=content,
            usage=self.estimate_cost(request.model, prompt_tokens, completion_tokens),
            finish_reason=finish_reason,
            raw=raw,
        )

    def stream(self, request: GenerateRequest) -> Iterator[str]:
        if not self.supports_streaming(request.model):
            raise self._unsupported("streaming")
        if self.mock_mode:
            yield from request.text().split()
            return
        for line in self._transport.stream(
            "POST",
            f"{self.base_url}/api/chat",
            headers={},
            json=self._chat_payload(request, stream=True),
        ):
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise ProviderError(
                    "Ollama stream returned invalid JSON",
                    category=ProviderErrorCategory.PARSING,
                    provider=self.name,
                ) from error
            if content := event.get("message", {}).get("content"):
                yield str(content)

    def embed(self, texts: list[str], model: str | None = None) -> EmbeddingResponse:
        selected = model or next(
            (item.name for item in self.discover_models() if item.embedding), None
        )
        if selected is None or not self.capabilities(selected).supports(Capability.EMBEDDINGS):
            raise self._unsupported("embeddings")
        tokens = sum(self.estimate_tokens(text) for text in texts)
        if self.mock_mode:
            vectors = [[round((ord(char) % 31) / 31, 6) for char in text[:16]] for text in texts]
        else:
            raw = self._transport.request(
                "POST",
                f"{self.base_url}/api/embed",
                headers={},
                json={"model": selected, "input": texts},
            )
            vectors = raw.get("embeddings", [])
        return EmbeddingResponse(
            provider=self.name,
            model=selected,
            vectors=vectors,
            usage=self.estimate_cost(selected, tokens, 0),
        )

    def health(self) -> dict[str, Any]:
        try:
            models = self.discover_models(refresh=True)
            return {
                "provider": self.name,
                "available": True,
                "mock": self.mock_mode,
                "base_url": self.base_url,
                "models": len(models),
                "checked_at": datetime.now(UTC).isoformat(),
            }
        except ProviderError as error:
            return {
                "provider": self.name,
                "available": False,
                "mock": False,
                "base_url": self.base_url,
                "models": 0,
                "error": str(error),
                "checked_at": datetime.now(UTC).isoformat(),
            }

    def _chat_payload(self, request: GenerateRequest, *, stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": request.messages or [{"role": "user", "content": request.text()}],
            "stream": stream,
            "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
        }
        if request.json_mode:
            payload["format"] = "json"
        if request.tools:
            payload["tools"] = request.tools
        return payload

    def _unsupported(self, capability: str) -> ProviderError:
        return ProviderError(
            f"ollama does not support {capability} for the selected model",
            category=ProviderErrorCategory.UNSUPPORTED_CAPABILITY,
            provider=self.name,
        )


ollama_provider = OllamaProvider()
