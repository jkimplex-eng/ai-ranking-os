from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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


class SocialPlatform(StrEnum):
    TELEGRAM = "TELEGRAM"
    INSTAGRAM = "INSTAGRAM"
    YOUTUBE = "YOUTUBE"
    VK = "VK"


class SocialSourceCreate(BaseModel):
    platform: SocialPlatform
    profile_url: HttpUrl
    external_id: str = Field(min_length=1, max_length=300)
    access_token: str | None = Field(default=None, min_length=8, max_length=4000)


class SocialPostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_post_id: str
    url: str
    title: str | None
    content: str
    published_at: datetime
    views: int | None
    likes: int | None
    comments: int | None
    shares: int | None
    engagement_rate: float | None
    significance_score: float


class SocialSourceRead(BaseModel):
    id: int
    competitor_id: int
    platform: SocialPlatform
    profile_url: str
    external_id: str
    configured: bool
    active: bool
    status: str
    last_scanned_at: datetime | None
    next_scan_at: datetime | None
    last_error: str | None
    posts: list[SocialPostRead] = Field(default_factory=list)


class SocialDashboardRead(BaseModel):
    competitor_id: int
    sources: list[SocialSourceRead]
    total_posts: int
    limitation: str = (
        "Значимость публикации основана на доступных публичных метриках и повторных "
        "наблюдениях; она не доказывает влияние на выдачу AI."
    )
