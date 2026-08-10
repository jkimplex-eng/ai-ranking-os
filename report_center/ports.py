from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ReportSourceItem:
    research_id: int
    project_id: int
    title: str
    status: str
    visibility_score: float | None
    score_version: str | None
    created_at: datetime


class ReportSource(Protocol):
    def list_reports(self, project_id: int | None = None) -> list[ReportSourceItem]: ...

    def export_payload(self, research_id: int) -> dict: ...
