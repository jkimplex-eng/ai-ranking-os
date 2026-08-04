from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AnalyticsRecord:
    observed_at: datetime
    dimensions: dict[str, str] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)


class AnalyticsDataSource(Protocol):
    """Public read port for any platform analytics producer."""

    def records(
        self, date_from: datetime | None = None, date_to: datetime | None = None
    ) -> list[AnalyticsRecord]: ...
