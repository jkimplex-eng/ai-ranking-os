from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.app.providers.capabilities import ModelCapabilities, Region
from backend.app.providers.pricing import ModelPrice, UsageCost
from backend.app.providers.tokenizer import estimate_tokens


class GenerateRequest(BaseModel):
    model: str
    prompt: str | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)
    max_tokens: int = Field(default=512, ge=1)
    temperature: float = Field(default=0.2)
    json_mode: bool = False
    tools: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def text(self) -> str:
        return self.prompt or " ".join(
            str(message.get("content", "")) for message in self.messages
        )


class GenerateResponse(BaseModel):
    provider: str
    model: str
    content: str
    usage: UsageCost
    finish_reason: str = "stop"
    citations: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    cached: bool = False
    raw: dict[str, Any] = Field(default_factory=dict)


class EmbeddingResponse(BaseModel):
    provider: str
    model: str
    vectors: list[list[float]]
    usage: UsageCost


class ProviderModel(BaseModel):
    id: str
    region: Region
    capabilities: ModelCapabilities
    price: ModelPrice


class Provider(ABC):
    name: str
    region: Region

    @abstractmethod
    def generate(self, request: GenerateRequest) -> GenerateResponse: ...

    @abstractmethod
    def stream(self, request: GenerateRequest) -> Iterator[str]: ...

    @abstractmethod
    def embed(self, texts: list[str], model: str | None = None) -> EmbeddingResponse: ...

    @abstractmethod
    def health(self) -> dict[str, Any]: ...

    @abstractmethod
    def models(self) -> list[ProviderModel]: ...

    def capabilities(self, model: str) -> ModelCapabilities:
        return self._model(model).capabilities

    def estimate_tokens(self, value: str) -> int:
        return estimate_tokens(value)

    def estimate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> UsageCost:
        price = self._model(model).price
        return UsageCost(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost=price.estimate(prompt_tokens, completion_tokens),
            currency=price.currency,
            provider=self.name,
            model=model,
        )

    def supports_streaming(self, model: str) -> bool:
        return self.capabilities(model).supports("streaming")

    def supports_function_calling(self, model: str) -> bool:
        return self.capabilities(model).supports("function_calling")

    def supports_json_mode(self, model: str) -> bool:
        return self.capabilities(model).supports("json_mode")

    def _model(self, model: str) -> ProviderModel:
        for item in self.models():
            if item.id == model:
                return item
        raise ValueError(f"Unknown {self.name} model: {model}")
