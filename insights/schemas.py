from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from benchmark.schemas import SUPPORTED_METRICS


class InsightType(StrEnum):
    GROWTH = "GROWTH"
    DECLINE = "DECLINE"
    ANOMALY = "ANOMALY"
    LEADER = "LEADER"
    KEY_CHANGE = "KEY_CHANGE"
    RECOMMENDATION = "RECOMMENDATION"


class InsightSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class InsightRequest(BaseModel):
    entity_ids: list[str] = Field(default_factory=list, max_length=1000)
    metrics: list[str] = Field(default_factory=lambda: list(SUPPORTED_METRICS), min_length=1)
    date_from: datetime | None = None
    date_to: datetime | None = None
    change_threshold: float = Field(default=5, ge=0, le=100)
    anomaly_z_threshold: float = Field(default=2, ge=1, le=10)
    leader_count: int = Field(default=3, ge=1, le=100)

    @model_validator(mode="after")
    def validate_request(self) -> "InsightRequest":
        unknown = set(self.metrics) - set(SUPPORTED_METRICS)
        if unknown:
            raise ValueError(f"Unsupported metrics: {', '.join(sorted(unknown))}")
        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("metrics must be unique")
        if len(set(self.entity_ids)) != len(self.entity_ids):
            raise ValueError("entity_ids must be unique")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
        return self


class InsightRead(BaseModel):
    id: int
    insight_type: InsightType
    severity: InsightSeverity
    entity_id: str | None
    metric: str | None
    title: str
    description: str
    previous_value: float | None
    current_value: float | None
    absolute_change: float | None
    percentage_change: float | None
    confidence: float = Field(ge=0, le=1)
    evidence: dict[str, object]
    recommendation: str | None


class InsightResult(BaseModel):
    id: int
    engine_version: str
    source_record_count: int = Field(ge=0)
    insight_count: int = Field(ge=0)
    calculated_at: datetime
    request: InsightRequest
    insights: list[InsightRead]


class InsightRunSummary(BaseModel):
    id: int
    engine_version: str
    source_record_count: int = Field(ge=0)
    insight_count: int = Field(ge=0)
    calculated_at: datetime


class InsightRunPage(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    items: list[InsightRunSummary]
