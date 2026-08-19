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
    evidence_level: str
    metric_deltas: dict[str, float]
    provider_deltas: dict[str, dict[str, float]]
    sample_size: int
    baseline_sample_size: int
    followup_sample_size: int
    matched_pairs: int
    failed_responses: int
    confidence_score: float = Field(ge=0, le=1)
    confidence_method: str
    evidence_matrix: dict
    limitations: list[str]
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
    evidence_level: str
    positive_experiments: int
    negative_experiments: int
    neutral_experiments: int
    last_observed_at: datetime | None
    limitations: list[str]
    algorithm_version: str
    updated_at: datetime


class LearningSummary(BaseModel):
    entity_id: UUID
    experiments: list[ExperimentRead]
    influence_estimates: list[InfluenceEstimateRead]
    status: str
    explanation: str
