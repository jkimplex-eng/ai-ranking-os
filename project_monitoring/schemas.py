from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class MonitorFrequency(StrEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class MonitorModel(BaseModel):
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)


class ProjectMonitorUpsert(BaseModel):
    template_research_id: int = Field(ge=1)
    frequency: MonitorFrequency
    models: list[MonitorModel] = Field(min_length=1, max_length=20)
    query: str | None = Field(default=None, min_length=1, max_length=100_000)
    enabled: bool = True


class ProjectMonitorRead(BaseModel):
    id: int
    project_id: int
    schedule_id: int
    template_research_id: int
    frequency: MonitorFrequency
    enabled: bool
    query: str | None
    next_run_at: datetime
    created_at: datetime
    updated_at: datetime
