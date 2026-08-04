from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from recommendation.models import RecommendationPriority
from recommendation.schemas import RecommendationRead


class RecommendationTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_code: str
    recommendation_type: str
    title: str
    description: str
    steps: list[str] = Field(min_length=1)
    expected_result: str
    estimated_time: str
    priority: RecommendationPriority
    version: str
    created_at: datetime


class ActionPlanItem(BaseModel):
    recommendation: RecommendationRead
    template: RecommendationTemplateRead | None
    steps: list[str]
    expected_effect: str
    estimated_time: str | None


class ActionPlan(BaseModel):
    research_id: int
    recommendation_execution_id: int
    engine_version: str
    generated_at: datetime
    items: list[ActionPlanItem]
