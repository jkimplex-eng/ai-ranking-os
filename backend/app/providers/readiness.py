import os
from threading import Lock
from time import monotonic
from typing import ClassVar

from sqlalchemy.orm import Session

from backend.app.llm_router.ports import ProviderReadinessPort, ProviderState
from backend.app.providers.cache import provider_cache
from backend.app.providers.credentials import credentials
from backend.app.providers.registry import registry


class RuntimeProviderReadiness(ProviderReadinessPort):
    """Provider-infrastructure implementation of the Router readiness port."""

    _health_cache: ClassVar[dict[str, tuple[float, bool]]] = {}
    _health_lock: ClassVar[Lock] = Lock()
    _health_ttl_seconds: ClassVar[float] = 30.0

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def state(self, provider_id: str) -> ProviderState:
        if self.db is not None:
            from provider_registry.models import ProviderRecord

            record = self.db.get(ProviderRecord, provider_id.casefold())
            if record is not None:
                aliases = {"AVAILABLE": "READY", "DEGRADED": "READY"}
                registry_state = ProviderState(
                    aliases.get(record.availability, record.availability)
                )
                if registry_state in {
                    ProviderState.DISABLED,
                    ProviderState.NOT_CONFIGURED,
                }:
                    return registry_state
        try:
            definition = registry.get(provider_id)
        except KeyError:
            return ProviderState.UNAVAILABLE
        if not definition.enabled:
            return ProviderState.DISABLED
        configured_mock = os.getenv("PROVIDER_MOCK_MODE")
        mock_mode = (
            configured_mock.casefold() not in {"false", "0", "no"}
            if configured_mock is not None
            else definition.mock
        )
        if mock_mode:
            return ProviderState.READY
        if definition.credential and not credentials.get(definition.credential, required=False):
            return ProviderState.NOT_CONFIGURED
        if definition.project_credential and not credentials.get(
            definition.project_credential, required=False
        ):
            return ProviderState.NOT_CONFIGURED
        return ProviderState.READY if self._healthy(provider_id) else ProviderState.UNAVAILABLE

    @classmethod
    def _healthy(cls, provider_id: str) -> bool:
        now = monotonic()
        with cls._health_lock:
            cached = cls._health_cache.get(provider_id)
            if cached and now - cached[0] < cls._health_ttl_seconds:
                return cached[1]
        try:
            from backend.app.providers.factory import factory

            available = bool(factory.create(provider_id).health().get("available"))
        except (KeyError, RuntimeError, ValueError):
            available = False
        with cls._health_lock:
            cls._health_cache[provider_id] = (now, available)
        return available

    @classmethod
    def invalidate(cls, provider_id: str) -> None:
        """Discard stale readiness after credentials are connected or revoked."""
        normalized = provider_id.casefold()
        with cls._health_lock:
            cls._health_cache.pop(normalized, None)
        provider_cache.delete(provider_cache.key("health", normalized, "True"))
        provider_cache.delete(provider_cache.key("health", normalized, "False"))
