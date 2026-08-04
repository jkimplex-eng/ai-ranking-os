from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from recommendation.models import (
    RecommendationExecutionStatus,
    RecommendationPriority,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RecommendationRead(ApiModel):
    id: int
    rule_id: int | None
    template_id: int | None
    recommendation_type: str
    priority: RecommendationPriority
    explanation: str
    metric: str
    metric_value: float = Field(ge=0, le=100)
    expected_effect: str
    created_at: datetime


class RecommendationSet(BaseModel):
    execution_id: int
    research_id: int
    status: RecommendationExecutionStatus
    engine_version: str
    score_version: str
    generated_at: datetime
    recommendations: list[RecommendationRead]
