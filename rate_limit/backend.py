from collections import defaultdict, deque
from dataclasses import dataclass
from threading import RLock
from time import monotonic

from rate_limit.ports import RateLimitDecision


@dataclass
class Bucket:
    tokens: float
    updated: float


class MemoryRateLimitBackend:
    def __init__(self):
        self.lock = RLock()
        self.buckets = {}
        self.windows = defaultdict(deque)

    def token_bucket(self, key, limit, window_seconds, burst=0, now=None):
        now = monotonic() if now is None else now
        capacity = limit + burst
        rate = limit / window_seconds
        with self.lock:
            bucket = self.buckets.setdefault(key, Bucket(float(capacity), now))
            bucket.tokens = min(capacity, bucket.tokens + (now - bucket.updated) * rate)
            bucket.updated = now
            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return RateLimitDecision(True, int(bucket.tokens), 0)
            return RateLimitDecision(False, 0, (1 - bucket.tokens) / rate)

    def sliding_window(self, key, limit, window_seconds, burst=0, now=None):
        now = monotonic() if now is None else now
        capacity = limit + burst
        with self.lock:
            values = self.windows[key]
            while values and values[0] <= now - window_seconds:
                values.popleft()
            if len(values) < capacity:
                values.append(now)
                return RateLimitDecision(True, capacity - len(values), 0)
            return RateLimitDecision(False, 0, max(0.0, values[0] + window_seconds - now))
