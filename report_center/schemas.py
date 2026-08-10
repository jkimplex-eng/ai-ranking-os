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


class ReportVersionRead(BaseModel):
    id: int
    research_id: int
    version: int
    checksum: str
    created_at: datetime


class ReportVersionComparison(BaseModel):
    research_id: int
    left_version: int
    right_version: int
    score_deltas: dict[str, float | None]
    added_entities: list[str]
    removed_entities: list[str]
    added_recommendations: list[str]
    removed_recommendations: list[str]
