from datetime import datetime

from pydantic import BaseModel, Field


class YandexAiObservation(BaseModel):
    research_id: int
    response_id: int
    query: str
    brand: str
    mentioned: bool
    recommended: bool
    citation_domains: list[str] = Field(default_factory=list)
    observed_at: datetime


class YandexQueryMapItem(BaseModel):
    query: str
    url: str | None = None
    impressions: float | None = None
    clicks: float | None = None
    ctr: float | None = None
    position: float | None = None
    demand: float | None = None
    yandex_ai_checked: bool = False
    brand_mentioned: bool | None = None
    evidence_status: str


class YandexOpportunity(BaseModel):
    priority: str
    priority_score: float
    query: str
    problem: str
    evidence: str
    affected_metric: str
    action: str
    target_url: str | None = None
    expected_range: str
    confidence: str
    effort: str
    duration: str
    verification: str


class YandexIntelligenceRead(BaseModel):
    id: int
    organization_id: int
    host_id: str
    host_url: str
    status: str
    evidence_status: str
    webmaster: dict
    yandex_ai: list[YandexAiObservation]
    query_map: list[YandexQueryMapItem]
    opportunities: list[YandexOpportunity]
    limitations: list[str]
    algorithm_version: str
    created_at: datetime


class YandexQuerySeedsRead(BaseModel):
    host_url: str
    queries: list[str]
    evidence_status: str
    snapshot_id: int
