from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PublicationCreate(BaseModel):
    entity_id: UUID
    research_id: int | None = Field(default=None, ge=1)
    url: AnyHttpUrl
    content_hash: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    title: str = Field(min_length=1, max_length=500)
    published_at: datetime


class ObservationCreate(BaseModel):
    research_id: int = Field(ge=1)
    response_id: int = Field(ge=1)
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    first_observed_at: datetime
    evidence_excerpt: str = Field(min_length=1, max_length=10_000)


class ObservationRead(ApiModel):
    id: int
    publication_id: int
    research_id: int
    response_id: int
    provider: str
    model: str
    first_observed_at: datetime
    evidence_excerpt: str
    created_at: datetime


class PublicationRead(ApiModel):
    id: int
    entity_id: UUID
    research_id: int | None
    url: str
    content_hash: str
    title: str
    published_at: datetime
    created_at: datetime
    observations: list[ObservationRead]


class ResearchLaboratory(BaseModel):
    research: dict[str, Any]
    score: dict[str, Any] | None
    provenance: dict[str, Any]
    models: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    entities: list[dict[str, Any]]
    graph: dict[str, Any]
    recommendations: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    publications: list[PublicationRead]


class ResearchDiff(BaseModel):
    left_research_id: int
    right_research_id: int
    metric_deltas: dict[str, float | None]
    response_changes: list[dict[str, Any]]
    entity_changes: dict[str, list[str]]
    source_changes: dict[str, list[str]]
    provider_signal_changes: list[dict[str, Any]]
    interpretation: str
