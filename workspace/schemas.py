from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    settings: dict[str, Any] | None = None


class WorkspaceResearchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: str
    created_at: datetime
    progress_percent: float


class WorkspaceReportItem(BaseModel):
    research_id: int
    title: str
    visibility_score: float | None
    calculated_at: datetime | None


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    settings: dict[str, Any]
    recent_research: list[WorkspaceResearchItem]
    recent_reports: list[WorkspaceReportItem]
    favorite_projects: list[dict[str, Any]] = Field(default_factory=list)
    total_research: int
    created_at: datetime
    updated_at: datetime
