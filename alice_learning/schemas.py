from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

FEATURE_NAMES = (
    "search_visibility",
    "landing_page_match",
    "independent_source_support",
    "content_completeness",
    "expertise_evidence",
    "freshness",
    "availability_clarity",
    "technical_health",
)


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ObservationRead(ApiModel):
    id: int
    research_id: int
    response_id: int
    brand: str
    query: str
    category: str
    provider: str
    model: str
    mentioned: bool
    recommended: bool
    cited: bool
    recommendation_rank: int | None
    source_domains: list[str]
    features: dict[str, float]
    feature_evidence: dict
    evidence_status: str
    feature_version: str
    observed_at: datetime


class TrainRequest(BaseModel):
    category: str = "UNIVERSAL"
    language: str = "ru"
    region: str = "RU"


class ModelRead(ApiModel):
    id: int
    category: str
    language: str
    region: str
    status: str
    model_type: str
    intercept: float
    coefficients: dict[str, float]
    feature_statistics: dict
    sample_size: int
    positive_samples: int
    negative_samples: int
    validation: dict
    limitations: list[str]
    algorithm_version: str
    trained_at: datetime


class PredictRequest(BaseModel):
    brand: str = Field(min_length=1, max_length=300)
    query: str = Field(min_length=3, max_length=2000)
    category: str = "UNIVERSAL"
    language: str = "ru"
    region: str = "RU"
    features: dict[str, float]

    @field_validator("features")
    @classmethod
    def validate_features(cls, value: dict[str, float]) -> dict[str, float]:
        unknown = sorted(set(value) - set(FEATURE_NAMES))
        if unknown:
            raise ValueError("Неизвестные признаки: " + ", ".join(unknown))
        missing = sorted(set(FEATURE_NAMES) - set(value))
        if missing:
            raise ValueError("Не заполнены признаки: " + ", ".join(missing))
        if any(not 0 <= item <= 1 for item in value.values()):
            raise ValueError("Все признаки должны находиться в диапазоне 0–1")
        return value


class Counterfactual(BaseModel):
    feature: str
    current_value: float
    target_value: float
    current_probability: float
    predicted_probability: float
    predicted_delta: float
    action: str
    evidence_level: str


class PredictionRead(ApiModel):
    id: int
    model_id: int
    brand: str
    query: str
    features: dict[str, float]
    probability: float
    confidence: float
    counterfactuals: list[Counterfactual]
    explanation: dict
    evidence_status: str
    algorithm_version: str
    created_at: datetime


class DashboardRead(BaseModel):
    status: str
    brand: str | None
    observation_count: int
    recommendation_count: int
    baseline_probability: float | None
    model: ModelRead | None
    top_factors: list[dict]
    recommended_actions: list[Counterfactual]
    recent_predictions: list[PredictionRead]
    limitations: list[str]
