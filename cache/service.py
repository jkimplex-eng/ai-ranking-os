from collections.abc import Callable
from typing import Any

from cache.ports import CacheBackend


class CacheService:
    def __init__(self, backend: CacheBackend):
        self.backend = backend

    def get(self, key):
        return self.backend.get(key)

    def set(self, key, value, ttl_seconds=300, tags=None):
        self.backend.set(key, value, ttl_seconds, set(tags or []))

    def read_through(self, key, loader: Callable[[], Any], ttl_seconds=300, tags=None):
        value = self.get(key)
        if value is None:
            value = loader()
            self.set(key, value, ttl_seconds, tags)
        return value

    def write_through(self, key, value, writer: Callable[[Any], Any], ttl_seconds=300, tags=None):
        result = writer(value)
        self.set(key, result, ttl_seconds, tags)
        return result

    def warm(self, entries: list[dict[str, Any]]):
        for entry in entries:
            self.set(
                entry["key"], entry["value"], entry.get("ttl_seconds", 300), entry.get("tags", [])
            )
        return len(entries)
