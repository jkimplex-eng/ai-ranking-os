from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderUsageFact:
    provider: str
    model: str
    latency_ms: float
    cost: float
    tokens: int


class ResearchUsageSource(Protocol):
    def usage(self, research_id: int) -> list[ProviderUsageFact]: ...
