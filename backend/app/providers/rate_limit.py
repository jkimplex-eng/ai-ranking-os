from collections import deque
from dataclasses import dataclass, field
from threading import BoundedSemaphore, RLock
from time import monotonic

from backend.app.providers.exceptions import ProviderError, ProviderErrorCategory


@dataclass
class RateLimitPolicy:
    rpm: int = 60
    tpm: int = 100_000
    concurrent_requests: int = 5
    retry_budget: int = 3


@dataclass
class _Window:
    requests: deque[float] = field(default_factory=deque)
    tokens: deque[tuple[float, int]] = field(default_factory=deque)


class ProviderRateLimiter:
    def __init__(self, provider: str, policy: RateLimitPolicy) -> None:
        self.provider = provider
        self.policy = policy
        self._window = _Window()
        self._lock = RLock()
        self._concurrency = BoundedSemaphore(policy.concurrent_requests)

    def acquire(self, estimated_tokens: int) -> None:
        now = monotonic()
        with self._lock:
            cutoff = now - 60
            while self._window.requests and self._window.requests[0] <= cutoff:
                self._window.requests.popleft()
            while self._window.tokens and self._window.tokens[0][0] <= cutoff:
                self._window.tokens.popleft()
            used_tokens = sum(tokens for _, tokens in self._window.tokens)
            if len(self._window.requests) >= self.policy.rpm:
                self._raise()
            if used_tokens + estimated_tokens > self.policy.tpm:
                self._raise()
            if not self._concurrency.acquire(blocking=False):
                self._raise()
            self._window.requests.append(now)
            self._window.tokens.append((now, estimated_tokens))

    def release(self) -> None:
        self._concurrency.release()

    def _raise(self) -> None:
        raise ProviderError(
            "Provider rate limit exceeded",
            category=ProviderErrorCategory.RATE_LIMIT,
            provider=self.provider,
            retryable=True,
            status_code=429,
        )
