from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TrendObservation:
    research_id: int
    observed_at: datetime
    visibility: float
    mention: float
    recommendation: float
    citation: float
    coverage: float
    confidence: float

    def metrics(self) -> dict[str, float]:
        return {
            "visibility": self.visibility,
            "mention": self.mention,
            "recommendation": self.recommendation,
            "citation": self.citation,
            "coverage": self.coverage,
            "confidence": self.confidence,
        }


class TrendDataSource(Protocol):
    """Public read boundary consumed by the trend domain."""

    def history(self, entity_id: UUID) -> list[TrendObservation]: ...


class TrendDataUnavailableError(LookupError):
    """No scored observations exist for an entity."""

