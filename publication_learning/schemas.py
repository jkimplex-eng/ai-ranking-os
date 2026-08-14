from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ExperimentRead(ApiModel):
    id: int
    publication_id: int
    entity_id: UUID
    baseline_research_id: int
    followup_research_id: int
    matrix_fingerprint: str
    status: str
    causality_status: str
    evidence_grade: str
    metric_deltas: dict[str, float]
    provider_deltas: dict[str, dict[str, float]]
    sample_size: int
    algorithm_version: str
    evaluated_at: datetime


class InfluenceEstimateRead(ApiModel):
    id: int
    resource_domain: str
    channel: str
    content_type: str
    metric: str
    provider: str
    model: str
    category: str
    language: str
    region: str
    sample_size: int
    expected_delta: float
    confidence_min: float
    confidence_max: float
    confidence_score: float = Field(ge=0, le=1)
    evidence_grade: str
    algorithm_version: str
    updated_at: datetime


class LearningSummary(BaseModel):
    entity_id: UUID
    experiments: list[ExperimentRead]
    influence_estimates: list[InfluenceEstimateRead]
    status: str
    explanation: str
