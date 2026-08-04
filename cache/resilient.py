from collections.abc import Callable
from typing import Any

from backend.app.monitoring.metrics import BACKEND_AVAILABLE, BACKEND_ERRORS
from cache.ports import CacheBackend
from hardening.service import CircuitBreaker, CircuitOpenError


class ResilientCacheBackend:
    """Fail-open cache facade: Redis failure degrades to bounded process memory."""

    def __init__(
        self,
        primary: CacheBackend,
        fallback: CacheBackend,
        *,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.breaker = breaker or CircuitBreaker(failure_threshold=3, recovery_seconds=15)
        self.degraded = False
        self.errors = 0

    def _execute(self, operation: str, primary: Callable[[], Any], fallback: Callable[[], Any]):
        try:
            result = self.breaker.execute(primary)
            self.degraded = False
            BACKEND_AVAILABLE.labels(backend="redis").set(1)
            return result
        except (Exception, CircuitOpenError):
            self.degraded = True
            self.errors += 1
            BACKEND_ERRORS.labels(backend="redis", operation=operation).inc()
            BACKEND_AVAILABLE.labels(backend="redis").set(0)
            return fallback()

    def get(self, key: str):
        value = self._execute("get", lambda: self.primary.get(key), lambda: None)
        return self.fallback.get(key) if value is None else value

    def set(self, key: str, value: Any, ttl_seconds: int, tags: set[str]) -> None:
        self.fallback.set(key, value, ttl_seconds, tags)
        self._execute("set", lambda: self.primary.set(key, value, ttl_seconds, tags), lambda: None)

    def delete(self, key: str) -> bool:
        fallback_result = self.fallback.delete(key)
        return bool(
            self._execute("delete", lambda: self.primary.delete(key), lambda: fallback_result)
        )

    def invalidate_tag(self, tag: str) -> int:
        fallback_result = self.fallback.invalidate_tag(tag)
        return int(
            self._execute(
                "invalidate_tag",
                lambda: self.primary.invalidate_tag(tag),
                lambda: fallback_result,
            )
        )

    def stats(self) -> dict[str, int | bool | str]:
        fallback_stats = self.fallback.stats()
        return {
            **fallback_stats,
            "backend": "memory" if self.degraded else "redis",
            "degraded": self.degraded,
            "backend_errors": self.errors,
        }
