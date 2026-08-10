from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class MonitorScheduleRequest:
    name: str
    research_id: int
    frequency: str
    models: list[dict[str, str]]
    query: str | None
    enabled: bool


@dataclass(frozen=True)
class MonitorScheduleResult:
    schedule_id: int
    next_run_at: datetime


class SchedulerPort(Protocol):
    def validate_template(self, research_id: int, project_id: int) -> bool: ...
    def create(self, request: MonitorScheduleRequest) -> MonitorScheduleResult: ...
    def update(
        self, schedule_id: int, request: MonitorScheduleRequest
    ) -> MonitorScheduleResult: ...
    def delete(self, schedule_id: int) -> None: ...
