import os
from datetime import UTC, datetime
from threading import Event
from typing import Any

from pydantic import BaseModel, Field


class ProviderRequest(BaseModel):
    model: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    prompt: str | None = None
    max_tokens: int = Field(default=512, ge=1)
    temperature: float = Field(default=0.2, ge=0, le=2)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderResponse(BaseModel):
    provider: str
    model: str
    content: str
    input_tokens: int
    output_tokens: int
    finish_reason: str
    created_at: datetime
    mock: bool = True


class BaseMockProvider:
    provider_name = "base"
    credential_env = ""

    @property
    def configured(self) -> bool:
        return bool(os.getenv(self.credential_env, "mock-credential"))

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "status": "available" if self.configured else "unconfigured",
            "mock": True,
        }

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        prompt = request.prompt or " ".join(
            str(message.get("content", "")) for message in request.messages
        )
        content = f"[{self.provider_name}:{request.model}] {prompt}".strip()
        return ProviderResponse(
            provider=self.provider_name,
            model=request.model,
            content=content,
            input_tokens=max(1, len(prompt) // 4),
            output_tokens=max(1, len(content) // 4),
            finish_reason="stop",
            created_at=datetime.now(UTC),
        )

    def as_executor_adapter(
        self,
        payload: dict[str, Any],
        cancellation: Event,
    ) -> dict[str, Any]:
        if cancellation.is_set():
            raise RuntimeError("Execution cancelled")
        model = str(payload.get("model", f"{self.provider_name}-default"))
        request = ProviderRequest(
            model=model,
            prompt=str(payload.get("query", payload.get("prompt", ""))),
            max_tokens=int(payload.get("max_tokens", 512)),
            metadata=payload.get("metadata", {}),
        )
        return self.complete(request).model_dump(mode="json")

