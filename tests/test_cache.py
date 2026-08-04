from fastapi.testclient import TestClient

from backend.app.main import app
from cache.backend import MemoryCacheBackend
from cache.service import CacheService


def test_cache_features():
    backend = MemoryCacheBackend()
    service = CacheService(backend)
    calls = []
    assert (
        service.read_through("k", lambda: calls.append(1) or {"v": 1}, tags=["entity:1"])["v"] == 1
    )
    assert service.read_through("k", lambda: None)["v"] == 1 and len(calls) == 1
    assert backend.invalidate_tag("entity:1") == 1 and service.get("k") is None
    assert backend.stats()["hits"] == 1


def test_cache_api():
    client = TestClient(app)
    assert (
        client.post(
            "/cache/warm", json={"entries": [{"key": "api-k", "value": 1, "tags": ["t"]}]}
        ).json()["warmed"]
        == 1
    )
    assert client.post("/cache/invalidate", json={"tag": "t"}).json()["invalidated"] == 1
    assert "/cache/stats" in app.openapi()["paths"]
