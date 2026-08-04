from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from trend.models import TrendDirection


class TrendMetric(StrEnum):
    VISIBILITY = "visibility"
    MENTION = "mention"
    RECOMMENDATION = "recommendation"
    CITATION = "citation"
    COVERAGE = "coverage"
    CONFIDENCE = "confidence"


class TrendPointRead(BaseModel):
    research_id: int
    observed_at: datetime
    value: float = Field(ge=0, le=100)
    moving_average: float = Field(ge=0, le=100)
    percentage_change: float | None
    direction: TrendDirection


class MetricTrend(BaseModel):
    entity_id: UUID
    series_id: int
    snapshot_id: int
    metric: TrendMetric
    direction: TrendDirection
    points: list[TrendPointRead]


class TrendSeriesRead(BaseModel):
    entity_id: UUID
    series_id: int
    snapshot_id: int
    model_version: str
    moving_average_window: int = Field(ge=1)
    generated_at: datetime
    metrics: list[MetricTrend]

