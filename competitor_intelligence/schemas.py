from datetime import date, datetime

from pydantic import BaseModel, Field


class CompetitorSnapshotRead(BaseModel):
    snapshot_date: date
    research_count: int
    response_count: int
    mention_count: int
    recommendation_count: int
    citation_count: int
    source_count: int
    observed_visibility_score: float
    evidence: dict
    algorithm_version: str


class CompetitorPublicationRead(BaseModel):
    url: str
    domain: str
    title: str | None
    observation_count: int
    provider_count: int
    research_count: int
    mention_observations: int
    recommendation_observations: int
    significance_score: float
    significance_label: str
    first_seen_at: datetime
    last_seen_at: datetime
    evidence_level: str = "OBSERVATION"
    explanation: str


class CompetitorAnalyticsRead(BaseModel):
    competitor_id: int
    name: str
    domains: list[str]
    active: bool
    latest_visibility_score: float | None
    visibility_delta: float | None
    snapshots: list[CompetitorSnapshotRead]
    publications: list[CompetitorPublicationRead]


class CompetitorDashboardRead(BaseModel):
    project_id: int
    monitoring_enabled: bool
    next_run_at: datetime | None
    methodology: str = "COMPETITOR_OBSERVATION_V1"
    limitation: str = (
        "Значимость отражает повторяемую связь публикации с упоминаниями в наблюдаемых "
        "AI-ответах и не доказывает причинное влияние на закрытые алгоритмы моделей."
    )
    competitors: list[CompetitorAnalyticsRead]


class DailyMonitoringRequest(BaseModel):
    enabled: bool = True
    template_research_id: int | None = Field(default=None, ge=1)

