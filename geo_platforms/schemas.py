from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PlatformFields(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    domain: str = Field(min_length=1, max_length=255)
    platform_type: str = Field(default="PUBLICATION", min_length=1, max_length=60)
    category: str = Field(default="UNIVERSAL", min_length=1, max_length=100)
    country: str = Field(default="GLOBAL", min_length=2, max_length=8)
    language: str = Field(default="ALL", min_length=2, max_length=16)
    source: str = Field(default="MANUAL", min_length=1, max_length=40)
    source_reference: str | None = None
    ai_engines: list[str] = Field(default_factory=list, max_length=20)
    domain_trust: float | None = Field(default=None, ge=0, le=100)
    topical_authority_score: float | None = Field(default=None, ge=0, le=100)
    ai_citation_history: int | None = Field(default=None, ge=0)
    allows_ai_crawlers: bool | None = None
    in_knowledge_graph: bool | None = None
    branded_mentions_90d: int | None = Field(default=None, ge=0)
    youtube_mentions: int | None = Field(default=None, ge=0)
    branded_anchors: int | None = Field(default=None, ge=0)
    branded_search_volume: float | None = Field(default=None, ge=0)
    schema_markup_types: list[str] | None = Field(default=None, max_length=20)
    has_direct_answer: bool | None = None
    content_freshness_days: int | None = Field(default=None, ge=0)
    has_structured_lists: bool | None = None
    self_contained_paragraph_score: float | None = Field(default=None, ge=0, le=100)
    cost_per_placement: Decimal | None = Field(default=None, ge=0)
    evidence: dict = Field(default_factory=dict)
    active: bool = True

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        from geo_platforms.service import normalize_domain

        return normalize_domain(value)


class PlatformCreate(PlatformFields):
    pass


class PlatformUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=8)
    language: str | None = Field(default=None, min_length=2, max_length=16)
    ai_engines: list[str] | None = Field(default=None, max_length=20)
    domain_trust: float | None = Field(default=None, ge=0, le=100)
    topical_authority_score: float | None = Field(default=None, ge=0, le=100)
    ai_citation_history: int | None = Field(default=None, ge=0)
    allows_ai_crawlers: bool | None = None
    in_knowledge_graph: bool | None = None
    branded_mentions_90d: int | None = Field(default=None, ge=0)
    youtube_mentions: int | None = Field(default=None, ge=0)
    branded_anchors: int | None = Field(default=None, ge=0)
    branded_search_volume: float | None = Field(default=None, ge=0)
    schema_markup_types: list[str] | None = Field(default=None, max_length=20)
    has_direct_answer: bool | None = None
    content_freshness_days: int | None = Field(default=None, ge=0)
    has_structured_lists: bool | None = None
    self_contained_paragraph_score: float | None = Field(default=None, ge=0, le=100)
    cost_per_placement: Decimal | None = Field(default=None, ge=0)
    evidence: dict | None = None
    active: bool | None = None


class PlatformRead(PlatformFields, ApiModel):
    id: UUID
    created_at: datetime
    updated_at: datetime


class ImportRequest(BaseModel):
    provider: str
    rows: list[dict] = Field(min_length=1, max_length=10000)


class ImportRead(ApiModel):
    id: UUID
    provider: str
    status: str
    rows_total: int
    rows_imported: int
    rows_failed: int
    errors: list[dict]
    created_at: datetime


class DiscoveryRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=1000)
    category: str = "UNIVERSAL"
    language: str = "ALL"


class DiscoveryResult(BaseModel):
    created: int
    existing: int
    platforms: list[PlatformRead]
