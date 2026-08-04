from threading import Event
from typing import Any, Protocol

from backend.app.providers.router_adapter import executor_adapters


class ProviderAdapter(Protocol):
    def __call__(self, payload: dict[str, Any], cancellation: Event) -> Any: ...


class ProviderUnavailableError(LookupError):
    """No adapter is registered for the provider."""


def _local_adapter(provider: str) -> ProviderAdapter:
    def execute(payload: dict[str, Any], cancellation: Event) -> dict[str, Any]:
        if cancellation.is_set():
            raise RuntimeError("Execution was cancelled")
        content = payload.get("query", payload.get("prompt", payload.get("input", payload)))
        return {"provider": provider, "content": content}

    return execute


class Dispatcher:
    """Provider-neutral adapter registry."""

    def __init__(self, providers: dict[str, ProviderAdapter] | None = None) -> None:
        defaults = {
            name: _local_adapter(name)
            for name in ("codex", "qwen", "deepseek", "claude", "gemini", "echo")
        }
        defaults.update(executor_adapters())
        self._providers = providers or defaults

    def register(self, provider: str, adapter: ProviderAdapter) -> None:
        self._providers[provider.casefold()] = adapter

    def dispatch(
        self,
        provider: str,
        payload: dict[str, Any],
        cancellation: Event,
    ) -> Any:
        adapter = self._providers.get(provider.casefold())
        if adapter is None:
            raise ProviderUnavailableError(f"Provider {provider} is not registered")
        return adapter(payload, cancellation)
