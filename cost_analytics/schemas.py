from pydantic import BaseModel


class CostBreakdown(BaseModel):
    key: str
    cost_usd: float
    tokens: int


class CostAnalyticsRead(BaseModel):
    total_cost_usd: float
    total_tokens: int
    free_tokens: int
    paid_tokens: int
    by_research: list[CostBreakdown]
    by_model: list[CostBreakdown]
    by_user: list[CostBreakdown]
    currency: str = "USD"
