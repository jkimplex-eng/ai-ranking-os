from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.llm_router.mode import RoutingMode
from query_executor.schemas import ExecutionMode, ExecutionPlan
from query_intent.schemas import IntentType


class ModelStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    DISABLED = "DISABLED"
    MAINTENANCE = "MAINTENANCE"


class ModelTier(StrEnum):
    ECONOMY = "ECONOMY"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    LOCAL = "LOCAL"


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class RouterStrategy(StrEnum):
    FASTEST = "FASTEST"
    CHEAPEST = "CHEAPEST"
    LOCAL_ONLY = "LOCAL_ONLY"
    FREE_ONLY = "FREE_ONLY"
    HIGHEST_QUALITY = "HIGHEST_QUALITY"
    BALANCED = "BALANCED"
    CUSTOM = "CUSTOM"


class Pricing(BaseModel):
    input_per_million: float = Field(ge=0)
    output_per_million: float = Field(ge=0)


class ModelCreate(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    provider: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=300)
    version: str = Field(default="1.0", min_length=1, max_length=100)
    release_date: datetime | None = None
    status: ModelStatus = ModelStatus.ACTIVE
    tier: ModelTier = ModelTier.STANDARD
    capabilities: list[str] = Field(default_factory=list)
    pricing: Pricing
    latency_ms: float = Field(gt=0)
    tokens_per_second: float = Field(default=0, ge=0)
    average_latency: float = Field(default=0, ge=0)
    benchmark_score: float = Field(default=0, ge=0, le=100)
    quality: float = Field(ge=0, le=1)
    availability: float = Field(ge=0, le=1)
    context_window: int = Field(gt=0)
    hallucination_rate: float = Field(ge=0, le=1)
    domains: list[str] = Field(default_factory=lambda: ["general"])
    languages: list[str] = Field(default_factory=lambda: ["en"])
    region: str = Field(default="GLOBAL", pattern="^(GLOBAL|RUSSIA)$")
    success_probability: float = Field(default=0.95, ge=0, le=1)
    reasoning: bool = False
    multimodal: bool = False
    embeddings: bool = False
    json_mode: bool = False
    tool_calling: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=300)
    version: str | None = Field(default=None, min_length=1, max_length=100)
    release_date: datetime | None = None
    status: ModelStatus | None = None
    tier: ModelTier | None = None
    capabilities: list[str] | None = None
    pricing: Pricing | None = None
    latency_ms: float | None = Field(default=None, gt=0)
    tokens_per_second: float | None = Field(default=None, ge=0)
    average_latency: float | None = Field(default=None, ge=0)
    benchmark_score: float | None = Field(default=None, ge=0, le=100)
    quality: float | None = Field(default=None, ge=0, le=1)
    availability: float | None = Field(default=None, ge=0, le=1)
    context_window: int | None = Field(default=None, gt=0)
    hallucination_rate: float | None = Field(default=None, ge=0, le=1)
    domains: list[str] | None = None
    languages: list[str] | None = None
    region: str | None = Field(default=None, pattern="^(GLOBAL|RUSSIA)$")
    success_probability: float | None = Field(default=None, ge=0, le=1)
    reasoning: bool | None = None
    multimodal: bool | None = None
    embeddings: bool | None = None
    json_mode: bool | None = None
    tool_calling: bool | None = None
    metadata: dict[str, Any] | None = None


class ModelRead(ModelCreate):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    updated_at: datetime
    circuit_state: CircuitState = CircuitState.CLOSED


class ModelList(BaseModel):
    items: list[ModelRead]
    total: int
    page: int
    page_size: int


class ModelVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: str
    version: str
    snapshot: dict[str, Any]
    created_at: datetime


class PolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    task_type: str | None = None
    strategy: RouterStrategy = RouterStrategy.BALANCED
    enabled: bool
    execution_mode: ExecutionMode
    top_k: int
    weights: dict[str, float]
    required_capabilities: list[str]
    daily_budget_usd: float | None
    monthly_budget_usd: float | None
    per_research_budget_usd: float | None = None
    settings: dict[str, Any]
    updated_at: datetime


class PolicyUpdate(BaseModel):
    enabled: bool | None = None
    task_type: str | None = Field(default=None, max_length=100)
    strategy: RouterStrategy | None = None
    execution_mode: ExecutionMode | None = None
    top_k: int | None = Field(default=None, ge=1, le=8)
    weights: dict[str, float] | None = None
    required_capabilities: list[str] | None = None
    daily_budget_usd: float | None = Field(default=None, gt=0)
    monthly_budget_usd: float | None = Field(default=None, gt=0)
    per_research_budget_usd: float | None = Field(default=None, gt=0)
    settings: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_weights(self) -> "PolicyUpdate":
        if self.weights is not None and abs(sum(self.weights.values()) - 1.0) > 1e-6:
            raise ValueError("Policy weights must sum to 1.0")
        return self


class RouteRequest(BaseModel):
    query: str = Field(min_length=1, max_length=100_000)
    correlation_id: str | None = Field(default=None, max_length=200)
    intent: IntentType | None = None
    policy_id: str | None = Field(default=None, max_length=100)
    strategy: RouterStrategy | None = None
    task_type: str | None = Field(default=None, max_length=100)
    routing_mode: RoutingMode | None = None
    context_tokens: int = Field(default=0, ge=0)
    max_output_tokens: int = Field(default=512, ge=1, le=100_000)
    domain: str = Field(default="general", max_length=100)
    language: str | None = Field(default=None, max_length=20)
    region: str | None = Field(default=None, pattern="^(GLOBAL|RUSSIA)$")
    required_capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScoreBreakdown(BaseModel):
    model_id: str
    provider: str
    total: float
    factors: dict[str, float]
    estimated_cost_usd: float


class RouteResponse(BaseModel):
    correlation_id: str
    intent: IntentType
    policy_id: str
    selected_models: list[str]
    scores: list[ScoreBreakdown]
    plan: ExecutionPlan
    estimated_cost_usd: float
    budget_downgraded: bool
    fallback_count: int
    router_latency_ms: float
    strategy: RouterStrategy = RouterStrategy.BALANCED
    routing_mode: RoutingMode = RoutingMode.HYBRID
    version: str = "1.0"


class HistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    correlation_id: str
    query: str
    intent: str
    policy_id: str
    selected_models: list[str]
    execution_mode: str
    routing_scores: dict[str, Any]
    estimated_cost_usd: float
    latency_ms: float
    fallback_count: int
    budget_downgraded: bool
    error: str | None
    created_at: datetime


class HistoryList(BaseModel):
    items: list[HistoryRead]
    total: int
    page: int
    page_size: int


class RouterStatus(BaseModel):
    status: str
    models: dict[str, int]
    policies: int
    circuit_breakers: dict[str, int]
    costs: dict[str, float]
    version: str = "1.0"


class CostEstimate(BaseModel):
    selected_models: list[str]
    estimated_cost_usd: float
    estimated_time_ms: float
    estimated_input_tokens: int
    estimated_output_tokens: int
    within_budget: bool
    currency: str = "USD"


class ActualCostSummary(BaseModel):
    execution_id: str
    actual_cost: float
    actual_tokens: int
    actual_time_ms: float
    providers: list[str]
    currency: str = "USD"
