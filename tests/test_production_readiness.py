from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cache.backend import MemoryCacheBackend
from rate_limit.backend import MemoryRateLimitBackend


def test_compose_does_not_gate_api_on_redis_health() -> None:
    compose = Path("docker-compose.yml").read_text()
    api_section = compose.split("  api:", 1)[1].split("  worker:", 1)[0]
    assert "service_healthy" in api_section
    assert "redis:" not in api_section.split("depends_on:", 1)[1]


def test_cache_and_rate_limit_are_thread_safe_under_load() -> None:
    cache = MemoryCacheBackend()
    limiter = MemoryRateLimitBackend()

    def request(index: int) -> bool:
        cache.set(f"key:{index}", index, 60, {"load"})
        assert cache.get(f"key:{index}") == index
        return limiter.token_bucket("shared", 100, 60, burst=20, now=0).allowed

    with ThreadPoolExecutor(max_workers=32) as pool:
        decisions = list(pool.map(request, range(200)))
    assert sum(decisions) == 120
    assert cache.stats()["keys"] == 200
