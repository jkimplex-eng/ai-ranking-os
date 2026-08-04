from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: float


class RateLimitProvider(Protocol):
    def check(self, key: str, limit: int, window_seconds: int, burst: int = 0): ...
