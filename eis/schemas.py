from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QueryEvidence(BaseModel):
    cep_coverage: float | None = Field(default=None, ge=0, le=100)
    semantic_similarity: float | None = Field(default=None, ge=0, le=100)
    serp_position: int | None = Field(
        default=None,
        ge=0,
        description="SERP position; use 0 when the resource was checked and was not indexed",
    )
    evidence_ids: list[str] = Field(default_factory=list, max_length=1000)
    failed_evidence_ids: list[str] = Field(default_factory=list, max_length=1000)


class EISCalculateRequest(BaseModel):
    platform_id: UUID
    query_id: UUID | None = None
    ai_engine: str = Field(min_length=1, max_length=60)
    model_type: str = Field(default="heuristic", pattern="^heuristic$")
    query_evidence: QueryEvidence = Field(default_factory=QueryEvidence)


class EISComponent(BaseModel):
    value: float | None
    numerator: float
    denominator: float
    inputs: dict[str, float | bool | None]
    weights: dict[str, float]
    exclusions: list[str]


class EISRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    platform_id: UUID
    query_id: UUID | None
    ai_engine: str
    model_type: str
    eis_value: float | None
    priority: str | None
    components: dict[str, EISComponent]
    signal_probabilities: dict[str, float | None]
    evidence: dict
    explanation: dict
    evidence_status: str
    methodology_version: str
    weight_set_version: str
    calculated_at: datetime


class EISBatchRequest(BaseModel):
    platform_ids: list[UUID] = Field(min_length=1, max_length=100)
    query_id: UUID | None = None
    ai_engine: str = Field(min_length=1, max_length=60)
    model_type: str = Field(default="heuristic", pattern="^heuristic$")
    query_evidence: QueryEvidence = Field(default_factory=QueryEvidence)


class EISPriorityItem(BaseModel):
    score: EISRead
    cost_efficiency: float | None


class EISBatchResult(BaseModel):
    items: list[EISPriorityItem]
    methodology_version: str
    limitations: list[str]
