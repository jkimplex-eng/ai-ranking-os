from collections.abc import Iterable
from typing import Any, Protocol

ExportRow = dict[str, Any]


class ExportRepository(Protocol):
    """Public batch-read boundary consumed by the Export Engine."""

    def rows(self, analytics_run_ids: list[int]) -> Iterable[ExportRow]: ...


class ExportSourceNotFoundError(LookupError):
    pass
