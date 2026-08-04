from threading import Event
from typing import Any

from backend.app.providers.base import GenerateRequest
from backend.app.providers.factory import ProviderFactory, factory


def executor_adapters(
    provider_factory: ProviderFactory = factory,
) -> dict[str, Any]:
    adapters = {}
    for provider in provider_factory.all():
        def execute(
            payload: dict[str, Any],
            cancellation: Event,
            current: Any = provider,
        ) -> dict[str, Any]:
            if cancellation.is_set():
                raise RuntimeError("Execution cancelled")
            request = GenerateRequest(
                model=str(payload.get("model", current.models()[0].id)),
                prompt=str(payload.get("query", payload.get("prompt", ""))),
                max_tokens=int(payload.get("max_tokens", 512)),
                metadata=payload.get("metadata", {}),
            )
            return current.generate(request).model_dump(mode="json")

        adapters[provider.name] = execute
    return adapters

