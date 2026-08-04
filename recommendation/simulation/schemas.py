from datetime import datetime

from pydantic import BaseModel, Field


class RecommendationSimulationRead(BaseModel):
    id: int
    recommendation_id: int
    recommendation_type: str
    metric: str
    current_metric: float = Field(ge=0, le=100)
    expected_metric_change: float = Field(ge=0, le=100)
    current_visibility: float = Field(ge=0, le=100)
    predicted_visibility: float = Field(ge=0, le=100)
    predicted_delta: float = Field(ge=0, le=100)
    confidence_min: float = Field(ge=0, le=100)
    confidence_expected: float = Field(ge=0, le=100)
    confidence_max: float = Field(ge=0, le=100)
    estimated_duration_days: int = Field(ge=1)
    model_version: str
    created_at: datetime


class SimulationResult(BaseModel):
    research_id: int
    recommendation_execution_id: int
    model_version: str
    simulated_at: datetime
    simulations: list[RecommendationSimulationRead]
