from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class WordstatConnectionCreate(BaseModel):
    folder_id: str = Field(min_length=3, max_length=200)
    auth_type: str = Field(default="API_KEY", pattern=r"^(API_KEY|IAM_TOKEN)$")
    credential: str = Field(min_length=10, max_length=4000)


class WordstatConnectionRead(BaseModel):
    connected: bool
    status: str
    folder_id: str | None = None
    auth_type: str | None = None
    last_checked_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None


class WordstatDiscoveryRequest(BaseModel):
    brand: str = Field(min_length=1, max_length=300)
    category: str = Field(min_length=2, max_length=500)
    region_ids: list[int] = Field(default_factory=list, max_length=50)
    device: str = Field(default="all", pattern=r"^(all|desktop|phone|tablet)$")
    limit: int = Field(default=20, ge=5, le=50)

    @field_validator("region_ids")
    @classmethod
    def unique_regions(cls, values: list[int]) -> list[int]:
        return list(dict.fromkeys(value for value in values if value > 0))


class WordstatQueryRead(BaseModel):
    query: str
    frequency: int = Field(ge=0)
    demand_rank: int = Field(ge=1)
    source_type: str
    branded: bool
    selected_for_alice: bool


class WordstatSnapshotRead(BaseModel):
    id: int
    organization_id: int
    brand: str
    category: str
    region_ids: list[int]
    device: str
    status: str
    queries: list[WordstatQueryRead]
    raw_count: int
    limitations: list[str]
    algorithm_version: str
    created_at: datetime


class WordstatQueryAnalyticsItem(BaseModel):
    query: str
    frequency: int
    demand_rank: int
    response_count: int
    mention_count: int
    recommendation_count: int
    mention_rate: float
    recommendation_rate: float
    competing_brands: list[str] = Field(default_factory=list)
    citation_domains: list[str] = Field(default_factory=list)
    evidence_status: str
    research_ids: list[int] = Field(default_factory=list)


class WordstatAnalyticsRead(BaseModel):
    snapshot_id: int
    brand: str
    category: str
    query_count: int
    checked_query_count: int
    total_frequency: int
    weighted_visibility: float | None
    numerator: float
    denominator: float
    status: str
    items: list[WordstatQueryAnalyticsItem]
    methodology_version: str
    limitations: list[str]
