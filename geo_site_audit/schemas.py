from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SiteAuditCreate(BaseModel):
    brand: str = Field(min_length=1, max_length=200)
    website_url: HttpUrl
    project_id: int | None = Field(default=None, ge=1)


class AuditCheck(BaseModel):
    code: str
    category: str
    title: str
    passed: bool
    points: float
    max_points: float
    evidence: str
    recommendation: str | None = None


class AuditOpportunity(BaseModel):
    priority: str
    problem: str
    affected_metric: str
    action: str
    expected_effect: str
    confidence: str
    effort: str
    verification: str


class SiteAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    brand: str
    website_url: str
    final_url: str
    score: float
    grade: str
    category_scores: dict[str, float]
    checks: list[AuditCheck]
    opportunities: list[AuditOpportunity]
    evidence: dict
    algorithm_version: str
    limitation: str
    created_at: datetime
