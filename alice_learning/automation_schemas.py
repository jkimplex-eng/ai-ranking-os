from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class AutomationPlanCreate(BaseModel):
    template_research_id: int = Field(ge=1)
    brand: str = Field(min_length=1, max_length=300)
    website_url: HttpUrl
    language: str = Field(default="ru", min_length=2, max_length=20)
    region: str = Field(default="RU", min_length=2, max_length=20)
    research_profile: str = Field(default="UNIVERSAL", max_length=40)
    routing_profile: str = Field(default="BALANCED", max_length=40)
    models: list[dict[str, str]] = Field(default_factory=list, max_length=20)
    repetitions: int = Field(default=3, ge=1, le=5)
    daily_query_limit: int = Field(default=6, ge=1, le=20)
    weekly_query_limit: int = Field(default=20, ge=4, le=60)
    daily_budget_usd: float = Field(default=2.0, gt=0, le=10_000)
    monthly_budget_usd: float = Field(default=30.0, gt=0, le=100_000)
    is_enabled: bool = True

    @model_validator(mode="after")
    def valid_budgets(self):
        if self.monthly_budget_usd < self.daily_budget_usd:
            raise ValueError("Месячный бюджет не может быть меньше дневного")
        for model in self.models:
            if not model.get("provider") or not model.get("model"):
                raise ValueError("Каждая модель должна содержать provider и model")
        return self


class AutomationPlanUpdate(BaseModel):
    repetitions: int | None = Field(default=None, ge=1, le=5)
    daily_query_limit: int | None = Field(default=None, ge=1, le=20)
    weekly_query_limit: int | None = Field(default=None, ge=4, le=60)
    daily_budget_usd: float | None = Field(default=None, gt=0, le=10_000)
    monthly_budget_usd: float | None = Field(default=None, gt=0, le=100_000)
    is_enabled: bool | None = None


class QuerySetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    plan_id: int
    version: int
    kind: str
    fingerprint: str
    queries: list[dict]
    source_metadata: dict
    created_at: datetime


class AutomationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    plan_id: int
    query_set_id: int
    run_kind: str
    status: str
    research_id: int | None
    task_count: int
    estimated_cost_usd: float
    actual_cost_usd: float | None
    result: dict
    error: str | None
    scheduled_for: datetime
    started_at: datetime
    finished_at: datetime | None


class AutomationPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    owner_user_id: int
    template_research_id: int
    brand: str
    website_url: str
    language: str
    region: str
    research_profile: str
    routing_profile: str
    models: list[dict]
    repetitions: int
    daily_query_limit: int
    weekly_query_limit: int
    daily_budget_usd: float
    monthly_budget_usd: float
    is_enabled: bool
    next_run_at: datetime
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RunNowRequest(BaseModel):
    kind: Literal["DAILY", "WEEKLY", "MONTHLY"] = "DAILY"


class AutomationDashboard(BaseModel):
    plans: list[AutomationPlanRead]
    latest_runs: list[AutomationRunRead]
    methodology: dict
