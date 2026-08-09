from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProviderRecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    research_id: int
    recommendation_type: str
    message: str
    recommended_provider: str
    expected_savings_usd: float
    expected_speedup_percent: float
    version: str
    created_at: datetime
