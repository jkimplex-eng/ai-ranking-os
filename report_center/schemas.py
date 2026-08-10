from datetime import datetime

from pydantic import BaseModel, Field


class ReportCatalogUpdate(BaseModel):
    tags: list[str] | None = Field(default=None, max_length=50)
    archived: bool | None = None


class ReportCatalogRead(BaseModel):
    research_id: int
    project_id: int
    title: str
    status: str
    visibility_score: float | None
    score_version: str | None
    tags: list[str]
    archived: bool
    created_at: datetime


class ReportCatalogPage(BaseModel):
    items: list[ReportCatalogRead]
    total: int
    offset: int
    limit: int
