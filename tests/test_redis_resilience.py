from redis.exceptions import RedisError

from cache.backend import MemoryCacheBackend
from cache.resilient import ResilientCacheBackend
from hardening.service import CircuitBreaker


class FailingRedis:
    def get(self, _key):
        raise RedisError("unavailable")

    def set(self, *_args):
        raise RedisError("unavailable")

    def delete(self, _key):
        raise RedisError("unavailable")

    def invalidate_tag(self, _tag):
        raise RedisError("unavailable")


def test_redis_failure_degrades_to_memory_without_blocking() -> None:
    backend = ResilientCacheBackend(
        FailingRedis(),
        MemoryCacheBackend(),
        breaker=CircuitBreaker(failure_threshold=1, recovery_seconds=60),
    )
    backend.set("research:1", {"score": 83}, 60, {"research"})
    assert backend.get("research:1") == {"score": 83}
    assert backend.stats()["degraded"] is True
    assert backend.stats()["backend_errors"] >= 2


def test_redis_failure_keeps_invalidation_safe() -> None:
    backend = ResilientCacheBackend(
        FailingRedis(),
        MemoryCacheBackend(),
        breaker=CircuitBreaker(failure_threshold=1, recovery_seconds=60),
    )
    backend.set("a", 1, 60, {"entity:1"})
    assert backend.invalidate_tag("entity:1") == 1
    assert backend.get("a") is None
