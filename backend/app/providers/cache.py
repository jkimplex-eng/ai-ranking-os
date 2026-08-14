from dataclasses import dataclass
from hashlib import sha256
from threading import RLock
from time import monotonic
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self, ttl_seconds: float = 300, max_entries: int = 10_000) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._values: dict[str, CacheEntry] = {}
        self._lock = RLock()

    @staticmethod
    def key(namespace: str, *parts: str) -> str:
        raw = "\x1f".join((namespace, *parts))
        return sha256(raw.encode()).hexdigest()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._values.get(key)
            if entry is None:
                return None
            if entry.expires_at <= monotonic():
                self._values.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        with self._lock:
            if len(self._values) >= self.max_entries:
                oldest = min(self._values, key=lambda item: self._values[item].expires_at)
                self._values.pop(oldest, None)
            self._values[key] = CacheEntry(
                value=value,
                expires_at=monotonic() + (ttl_seconds or self.ttl_seconds),
            )

    def delete(self, key: str) -> None:
        with self._lock:
            self._values.pop(key, None)


prompt_cache = TTLCache()
provider_cache = TTLCache(ttl_seconds=60)
response_cache = TTLCache()

