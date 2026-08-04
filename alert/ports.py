from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AlertObservation:
    research_id: int
    observed_at: datetime
    visibility: float
    confidence: float
    brand_recommendations: frozenset[str] = field(default_factory=frozenset)
    authoritative_citations: frozenset[str] = field(default_factory=frozenset)
    critical_recommendations: frozenset[str] = field(default_factory=frozenset)


class AlertDataSource(Protocol):
    """Read-only historical input required by Alert Engine."""

    def history(self, entity_id: UUID) -> list[AlertObservation]: ...


class AlertDataUnavailableError(LookupError):
    """An entity has insufficient scored history for evaluation."""

