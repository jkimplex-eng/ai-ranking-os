from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.llm_router.schemas import RoutingProfile
from research.models import (
    ResearchJobState,
    ResearchStatus,
    ResearchTaskStatus,
    ResponseProcessingStatus,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ResearchCreate(BaseModel):
    project_id: int | None = Field(default=None, ge=1)
    domain_id: int | None = Field(default=None, ge=1)
    entity_id: UUID | None = None
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    objective: str | None = None
    status: ResearchStatus = ResearchStatus.DRAFT
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchUpdate(BaseModel):
    project_id: int | None = Field(default=None, ge=1)
    domain_id: int | None = Field(default=None, ge=1)
    entity_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    objective: str | None = None
    status: ResearchStatus | None = None
    metadata: dict[str, Any] | None = None


class ResearchRead(ApiModel):
    id: int
    project_id: int | None
    domain_id: int | None
    entity_id: UUID | None
    title: str
    description: str | None
    objective: str | None
    status: ResearchStatus
    metadata: dict[str, Any] = Field(validation_alias="metadata_payload")
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    progress_percent: float
    created_at: datetime
    updated_at: datetime


class ResearchTaskCreate(BaseModel):
    research_id: int = Field(ge=1)
    query: str = Field(min_length=1, max_length=100_000)
    status: ResearchTaskStatus = ResearchTaskStatus.PENDING
    priority: int = Field(default=0, ge=-100, le=100)
    provider: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchTaskUpdate(BaseModel):
    query: str | None = Field(default=None, min_length=1, max_length=100_000)
    status: ResearchTaskStatus | None = None
    priority: int | None = Field(default=None, ge=-100, le=100)
    provider: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] | None = None


class ResearchTaskRead(ApiModel):
    id: int
    research_id: int
    query: str
    status: ResearchTaskStatus
    priority: int
    provider: str | None
    model: str | None
    metadata: dict[str, Any] = Field(validation_alias="metadata_payload")
    decision_task_id: int | None
    execution_id: int | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class ResponseCreate(BaseModel):
    research_task_id: int = Field(ge=1)
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    latency_ms: int | None = Field(default=None, ge=0)
    prompt: str = ""
    raw_response: dict[str, Any] | None = None
    normalized_response: dict[str, Any] | None = None
    cost: float = Field(default=0, ge=0)
    finished_at: datetime | None = None
    error_type: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def fill_total_tokens(self) -> "ResponseCreate":
        calculated = self.prompt_tokens + self.completion_tokens
        if self.total_tokens is None:
            self.total_tokens = calculated
        elif self.total_tokens != calculated:
            raise ValueError("total_tokens must equal prompt_tokens + completion_tokens")
        return self


class ResponseUpdate(BaseModel):
    provider: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    raw_payload: dict[str, Any] | None = None
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    latency_ms: int | None = Field(default=None, ge=0)


class ResponseRead(ApiModel):
    id: int
    research_task_id: int
    provider: str
    model: str
    content: str
    raw_payload: dict[str, Any]
    prompt: str
    raw_response: dict[str, Any]
    normalized_response: dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    latency_ms: int | None
    error_type: str | None
    error_message: str | None
    processing_status: ResponseProcessingStatus
    processing_error: str | None
    created_at: datetime
    finished_at: datetime


class ExtractedEntityRead(ApiModel):
    id: int
    response_id: int
    name: str
    canonical_name: str
    entity_type: str
    confidence: float
    aliases: list[str]
    knowledge_graph_id: str | None
    metadata: dict[str, Any] = Field(validation_alias="metadata_payload")


class ExtractedCitationRead(ApiModel):
    id: int
    response_id: int
    url: str | None
    title: str | None
    source: str | None
    excerpt: str | None
    position: int
    metadata: dict[str, Any] = Field(validation_alias="metadata_payload")


class ExtractedRecommendationRead(ApiModel):
    id: int
    response_id: int
    content: str
    rank: int
    confidence: float
    metadata: dict[str, Any] = Field(validation_alias="metadata_payload")


class ExtractionResultRead(BaseModel):
    response_id: int
    status: ResponseProcessingStatus
    entities: list[ExtractedEntityRead]
    brands: list[ExtractedEntityRead]
    products: list[ExtractedEntityRead]
    organizations: list[ExtractedEntityRead]
    people: list[ExtractedEntityRead]
    citations: list[ExtractedCitationRead]
    recommendations: list[ExtractedRecommendationRead]


class ResearchScoreRead(ApiModel):
    id: int
    research_id: int
    mention_score: float = Field(ge=0, le=100)
    recommendation_score: float = Field(ge=0, le=100)
    citation_score: float = Field(ge=0, le=100)
    coverage_score: float = Field(ge=0, le=100)
    confidence_score: float = Field(ge=0, le=100)
    visibility_score: float = Field(ge=0, le=100)
    calculated_at: datetime
    version: str


class ResearchReportRead(BaseModel):
    research: ResearchRead
    score: ResearchScoreRead | None
    responses: list[ResponseRead]
    entities: list[ExtractedEntityRead]
    citations: list[ExtractedCitationRead]
    recommendations: list[ExtractedRecommendationRead]


class ResearchComparisonRead(BaseModel):
    left_research_id: int
    right_research_id: int
    left_score_version: str
    right_score_version: str
    visibility_score_delta: float
    mention_score_delta: float
    recommendation_score_delta: float
    citation_score_delta: float
    coverage_score_delta: float
    confidence_score_delta: float
    new_entities: list[str]
    disappeared_entities: list[str]
    new_recommendations: list[str]
    disappeared_recommendations: list[str]


class ResearchHistoryItem(BaseModel):
    research_id: int
    created_at: datetime
    status: ResearchStatus
    visibility_score: float | None = Field(default=None, ge=0, le=100)
    score_version: str | None
    model_count: int = Field(ge=0)
    processed_response_count: int = Field(ge=0)


class ResearchHistoryAggregates(BaseModel):
    best_visibility: float | None = Field(default=None, ge=0, le=100)
    latest_visibility: float | None = Field(default=None, ge=0, le=100)
    average_visibility: float | None = Field(default=None, ge=0, le=100)
    research_count: int = Field(ge=0)
    first_to_latest_change: float | None


class ResearchHistoryPagination(BaseModel):
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)


class ResearchHistoryRead(BaseModel):
    entity_id: UUID
    items: list[ResearchHistoryItem]
    aggregates: ResearchHistoryAggregates
    pagination: ResearchHistoryPagination


class ResearchModelSelection(BaseModel):
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)


class ResearchRunRequest(BaseModel):
    models: list[ResearchModelSelection] = Field(default_factory=list, max_length=20)
    routing_profile: RoutingProfile = RoutingProfile.BALANCED
    query: str | None = Field(default=None, min_length=1, max_length=100_000)

    @model_validator(mode="before")
    @classmethod
    def reject_legacy_empty_selection(cls, value: Any) -> Any:
        if (
            isinstance(value, dict)
            and "models" in value
            and not value.get("models")
            and "routing_profile" not in value
        ):
            raise ValueError("models cannot be empty unless routing_profile is provided")
        return value


class ResearchEnqueueRequest(ResearchRunRequest):
    research_id: int = Field(ge=1)


class ResearchJobRead(ApiModel):
    id: int
    research_id: int
    state: ResearchJobState
    attempts: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
