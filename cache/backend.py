from datetime import UTC, datetime, timedelta
from threading import RLock


class MemoryCacheBackend:
    def __init__(self):
        self._values = {}
        self._tags = {}
        self._lock = RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key):
        with self._lock:
            item = self._values.get(key)
            if not item or item[1] <= datetime.now(UTC):
                self._misses += 1
                if item:
                    self.delete(key)
                return None
            self._hits += 1
            return item[0]

    def set(self, key, value, ttl_seconds, tags):
        with self._lock:
            self._values[key] = (
                value,
                datetime.now(UTC) + timedelta(seconds=ttl_seconds),
                set(tags),
            )
            for tag in tags:
                self._tags.setdefault(tag, set()).add(key)

    def delete(self, key):
        with self._lock:
            item = self._values.pop(key, None)
            if item:
                for tag in item[2]:
                    self._tags.get(tag, set()).discard(key)
            return item is not None

    def invalidate_tag(self, tag):
        with self._lock:
            keys = list(self._tags.pop(tag, set()))
        return sum(self.delete(key) for key in keys)

    def stats(self):
        return {
            "hits": self._hits,
            "misses": self._misses,
            "keys": len(self._values),
            "tags": len(self._tags),
        }
