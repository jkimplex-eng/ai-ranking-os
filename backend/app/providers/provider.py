import os
from collections.abc import Iterator
from time import perf_counter
from typing import Any

from backend.app.providers.base import (
    EmbeddingResponse,
    GenerateRequest,
    GenerateResponse,
    Provider,
    ProviderModel,
)
from backend.app.providers.cache import prompt_cache, provider_cache, response_cache
from backend.app.providers.credentials import CredentialManager, credentials
from backend.app.providers.exceptions import ProviderError, ProviderErrorCategory
from backend.app.providers.metrics import (
    AVAILABILITY,
    CACHE,
    COST,
    ERRORS,
    IN_FLIGHT,
    LATENCY,
    REQUESTS,
    TIMEOUTS,
    TOKENS,
)
from backend.app.providers.rate_limit import ProviderRateLimiter, RateLimitPolicy
from backend.app.providers.registry import ProviderDefinition, ProviderRegistry, registry
from backend.app.providers.stream import iter_sse
from backend.app.providers.transport import HTTPTransport


class ConfiguredProvider(Provider):
    def __init__(
        self,
        definition: ProviderDefinition,
        *,
        provider_registry: ProviderRegistry = registry,
        credential_manager: CredentialManager = credentials,
        transport: HTTPTransport | None = None,
    ) -> None:
        self.definition = definition
        self.name = definition.name
        self.region = definition.region
        self._registry = provider_registry
        self._credentials = credential_manager
        self._transport = transport or HTTPTransport(
            definition.timeout_seconds,
            max_retries=int(definition.rate_limits.get("retry_budget", 3)),
        )
        self._limiter = ProviderRateLimiter(
            self.name,
            RateLimitPolicy(**definition.rate_limits),
        )

    @property
    def mock_mode(self) -> bool:
        configured = os.getenv("PROVIDER_MOCK_MODE")
        return (
            configured.casefold() not in {"false", "0", "no"}
            if configured is not None
            else self.definition.mock
        )

    def models(self) -> list[ProviderModel]:
        return self.definition.models(self._registry.prices())

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        model = self._model(request.model)
        if request.json_mode and not self.supports_json_mode(request.model):
            raise self._unsupported("json_mode")
        if request.tools and not self.supports_function_calling(request.model):
            raise self._unsupported("function_calling")
        prompt_key = prompt_cache.key("prompt", request.text())
        prompt_tokens = prompt_cache.get(prompt_key)
        if prompt_tokens is None:
            prompt_tokens = self.estimate_tokens(request.text())
            prompt_cache.set(prompt_key, prompt_tokens)
        cache_key = response_cache.key(
            self.name,
            request.model,
            str(self.mock_mode),
            str(request.metadata.get("target_entity", "")),
            request.model_dump_json(exclude={"metadata"}),
        )
        if cached := response_cache.get(cache_key):
            CACHE.labels(provider=self.name, result="hit").inc()
            return GenerateResponse.model_validate({**cached, "cached": True})
        CACHE.labels(provider=self.name, result="miss").inc()
        self._limiter.acquire(prompt_tokens + request.max_tokens)
        IN_FLIGHT.labels(provider=self.name).inc()
        started = perf_counter()
        try:
            if self.mock_mode:
                target = str(request.metadata.get("target_entity", "the selected brand"))
                content = (
                    f"[{self.name}:{request.model}] {request.text()}\n"
                    f"We recommend {target} based on its documented market presence."
                ).strip()
                completion_tokens = self.estimate_tokens(content)
                raw: dict[str, Any] = {
                    "mock": True,
                    "citations": [
                        {
                            "url": "https://example.com/ai-visibility-source",
                            "title": "AI Visibility Source",
                            "source": "Demo Authority",
                        }
                    ],
                }
                finish_reason = "stop"
            else:
                raw = self._transport.request(
                    "POST",
                    self._generate_url(request.model),
                    headers=self._headers(),
                    json=self._generate_payload(request),
                )
                content, reported_prompt, reported_completion, finish_reason = self._parse_generate(
                    raw
                )
                prompt_tokens = reported_prompt or prompt_tokens
                completion_tokens = reported_completion or self.estimate_tokens(content)
            usage = self.estimate_cost(request.model, prompt_tokens, completion_tokens)
            response = GenerateResponse(
                provider=self.name,
                model=request.model,
                content=content,
                usage=usage,
                finish_reason=finish_reason,
                citations=[
                    citation if isinstance(citation, dict) else {"url": str(citation)}
                    for citation in raw.get("citations", [])
                ],
                metadata={
                    "region": self.region,
                    "mock": self.mock_mode,
                    **request.metadata,
                    "entities": [
                        {
                            "name": str(request.metadata["target_entity"]),
                            "type": "BRAND",
                            "confidence": 0.98,
                        }
                    ]
                    if request.metadata.get("target_entity")
                    else [],
                    "recommendations": [
                        {
                            "content": f"Increase authoritative mentions for {target}",
                            "confidence": 0.9,
                        }
                    ]
                    if self.mock_mode
                    else [],
                },
                raw=raw,
            )
            response_cache.set(cache_key, response.model_dump(mode="json"))
            self._record_success(model.id, usage, perf_counter() - started)
            return response
        except ProviderError as error:
            ERRORS.labels(provider=self.name, category=error.category).inc()
            if error.category == ProviderErrorCategory.TIMEOUT:
                TIMEOUTS.labels(provider=self.name).inc()
            REQUESTS.labels(provider=self.name, model=request.model, status="error").inc()
            raise
        finally:
            IN_FLIGHT.labels(provider=self.name).dec()
            self._limiter.release()

    def stream(self, request: GenerateRequest) -> Iterator[str]:
        if not self.supports_streaming(request.model):
            raise self._unsupported("streaming")
        if self.mock_mode:
            yield from request.text().split()
            return
        payload = self._generate_payload(request)
        if self.definition.protocol == "yandex":
            payload["completionOptions"]["stream"] = True
        else:
            payload["stream"] = True
        for event in iter_sse(
            self._transport.stream(
                "POST",
                self._stream_url(request.model),
                headers=self._headers(),
                json=payload,
            )
        ):
            if value := self._parse_stream_event(event):
                yield value

    def embed(self, texts: list[str], model: str | None = None) -> EmbeddingResponse:
        selected = model or next(
            (item.id for item in self.models() if item.capabilities.supports("embeddings")),
            None,
        )
        if selected is None or not self.capabilities(selected).supports("embeddings"):
            raise self._unsupported("embeddings")
        prompt_tokens = sum(self.estimate_tokens(text) for text in texts)
        if self.mock_mode:
            vectors = [
                [round((ord(char) % 31) / 31, 6) for char in (text[:16] or " ")] for text in texts
            ]
        else:
            if self.definition.protocol == "gemini":
                raw = self._transport.request(
                    "POST",
                    f"{self.definition.base_url}/models/{selected}:batchEmbedContents",
                    headers=self._headers(),
                    json={
                        "requests": [
                            {
                                "model": f"models/{selected}",
                                "content": {"parts": [{"text": text}]},
                            }
                            for text in texts
                        ]
                    },
                )
                vectors = [item["values"] for item in raw["embeddings"]]
            else:
                raw = self._transport.request(
                    "POST",
                    f"{self.definition.base_url}/embeddings",
                    headers=self._headers(),
                    json={"model": selected, "input": texts},
                )
                vectors = [item["embedding"] for item in raw["data"]]
        return EmbeddingResponse(
            provider=self.name,
            model=selected,
            vectors=vectors,
            usage=self.estimate_cost(selected, prompt_tokens, 0),
        )

    def health(self) -> dict[str, Any]:
        cache_key = provider_cache.key("health", self.name, str(self.mock_mode))
        if cached := provider_cache.get(cache_key):
            return cached
        configured = self.mock_mode or bool(
            self._credentials.get(self.definition.credential, required=False)
            if self.definition.credential
            else True
        )
        available = configured
        if configured and not self.mock_mode:
            try:
                self._transport.request(
                    "GET",
                    f"{self.definition.base_url}/models",
                    headers=self._headers(),
                )
            except ProviderError:
                available = False
        AVAILABILITY.labels(provider=self.name).set(1 if available else 0)
        result = {
            "provider": self.name,
            "region": self.region,
            "available": available,
            "mock": self.mock_mode,
            "models": [model.id for model in self.models()],
        }
        provider_cache.set(cache_key, result)
        return result

    def _headers(self) -> dict[str, str]:
        token = (
            self._credentials.get(self.definition.credential) if self.definition.credential else ""
        )
        if self.definition.protocol == "gemini":
            return {"Content-Type": "application/json", "x-goog-api-key": token}
        if self.definition.protocol == "anthropic":
            return {
                "Content-Type": "application/json",
                "x-api-key": token,
                "anthropic-version": "2023-06-01",
            }
        if self.definition.protocol == "yandex":
            folder = self._credentials.get(self.definition.project_credential)
            return {
                "Content-Type": "application/json",
                "Authorization": f"Api-Key {token}",
                "x-folder-id": str(folder),
            }
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def _generate_url(self, model: str) -> str:
        if self.definition.protocol == "gemini":
            return f"{self.definition.base_url}/models/{model}:generateContent"
        if self.definition.protocol == "anthropic":
            return f"{self.definition.base_url}/messages"
        if self.definition.protocol == "yandex":
            return f"{self.definition.base_url}/completion"
        return f"{self.definition.base_url}/chat/completions"

    def _stream_url(self, model: str) -> str:
        if self.definition.protocol == "gemini":
            return f"{self.definition.base_url}/models/{model}:streamGenerateContent?alt=sse"
        return self._generate_url(model)

    def _generate_payload(self, request: GenerateRequest) -> dict[str, Any]:
        messages = request.messages or [{"role": "user", "content": request.text()}]
        if self.definition.protocol == "gemini":
            return {
                "contents": [{"role": "user", "parts": [{"text": request.text()}]}],
                "generationConfig": {
                    "temperature": request.temperature,
                    "maxOutputTokens": request.max_tokens,
                },
            }
        if self.definition.protocol == "anthropic":
            return {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            }
        if self.definition.protocol == "yandex":
            folder = self._credentials.get(self.definition.project_credential)
            return {
                "modelUri": f"gpt://{folder}/{request.model}",
                "completionOptions": {
                    "stream": False,
                    "temperature": request.temperature,
                    "maxTokens": request.max_tokens,
                },
                "messages": messages,
            }
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}
        if request.tools:
            payload["tools"] = request.tools
        return payload

    def _parse_generate(self, raw: dict[str, Any]) -> tuple[str, int, int, str]:
        if self.definition.protocol == "gemini":
            content = raw["candidates"][0]["content"]["parts"][0]["text"]
            usage = raw.get("usageMetadata", {})
            return (
                content,
                int(usage.get("promptTokenCount", 0)),
                int(usage.get("candidatesTokenCount", 0)),
                raw["candidates"][0].get("finishReason", "STOP").casefold(),
            )
        if self.definition.protocol == "anthropic":
            usage = raw.get("usage", {})
            return (
                "".join(item.get("text", "") for item in raw["content"]),
                int(usage.get("input_tokens", 0)),
                int(usage.get("output_tokens", 0)),
                raw.get("stop_reason", "end_turn"),
            )
        if self.definition.protocol == "yandex":
            alternative = raw["result"]["alternatives"][0]
            usage = raw["result"].get("usage", {})
            return (
                alternative["message"]["text"],
                int(usage.get("inputTextTokens", 0)),
                int(usage.get("completionTokens", 0)),
                alternative.get("status", "FINAL"),
            )
        choice = raw["choices"][0]
        usage = raw.get("usage", {})
        return (
            choice["message"]["content"],
            int(usage.get("prompt_tokens", 0)),
            int(usage.get("completion_tokens", 0)),
            choice.get("finish_reason", "stop"),
        )

    def _parse_stream_event(self, event: dict[str, Any]) -> str:
        if self.definition.protocol == "gemini":
            return (
                event.get("candidates", [{}])[0]
                .get("content", {})
                .get(
                    "parts",
                    [{}],
                )[0]
                .get("text", "")
            )
        if self.definition.protocol == "anthropic":
            return event.get("delta", {}).get("text", "")
        if self.definition.protocol == "yandex":
            alternatives = event.get("result", {}).get("alternatives", [])
            return alternatives[0].get("message", {}).get("text", "") if alternatives else ""
        return event.get("choices", [{}])[0].get("delta", {}).get("content", "")

    def _record_success(self, model: str, usage: Any, duration: float) -> None:
        REQUESTS.labels(provider=self.name, model=model, status="success").inc()
        LATENCY.labels(provider=self.name, model=model).observe(duration)
        TOKENS.labels(provider=self.name, model=model, kind="prompt").inc(usage.prompt_tokens)
        TOKENS.labels(provider=self.name, model=model, kind="completion").inc(
            usage.completion_tokens
        )
        COST.labels(
            provider=self.name,
            model=model,
            currency=usage.currency,
        ).inc(usage.estimated_cost)

    def _unsupported(self, capability: str) -> ProviderError:
        return ProviderError(
            f"{self.name} does not support {capability}",
            category=ProviderErrorCategory.UNSUPPORTED_CAPABILITY,
            provider=self.name,
        )
