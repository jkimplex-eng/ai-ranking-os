from datetime import datetime

from pydantic import BaseModel, Field, model_validator

SUPPORTED_METRICS = (
    "visibility",
    "recommendation",
    "mention",
    "citation",
    "coverage",
    "confidence",
)


class BenchmarkRequest(BaseModel):
    entity_ids: list[str] = Field(default_factory=list, max_length=1000)
    metrics: list[str] = Field(default_factory=lambda: list(SUPPORTED_METRICS), min_length=1)
    date_from: datetime | None = None
    date_to: datetime | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "BenchmarkRequest":
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


class MetricBenchmark(BaseModel):
    value: float = Field(ge=0, le=100)
    rank: int = Field(ge=1)
    percentile: float = Field(ge=0, le=100)
    population_average: float = Field(ge=0, le=100)
    delta_from_average: float
    leader_value: float = Field(ge=0, le=100)
    delta_from_leader: float = Field(le=0)


class BenchmarkEntryRead(BaseModel):
    entity_id: str
    observation_count: int = Field(ge=1)
    metrics: dict[str, MetricBenchmark]
    overall_score: float = Field(ge=0, le=100)
    overall_rank: int = Field(ge=1)
    overall_percentile: float = Field(ge=0, le=100)


class BenchmarkResult(BaseModel):
    id: int
    engine_version: str
    metrics: list[str]
    entity_count: int = Field(ge=0)
    date_from: datetime | None
    date_to: datetime | None
    calculated_at: datetime
    entries: list[BenchmarkEntryRead]


class BenchmarkRunSummary(BaseModel):
    id: int
    engine_version: str
    metrics: list[str]
    entity_count: int = Field(ge=0)
    calculated_at: datetime


class BenchmarkRunPage(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    items: list[BenchmarkRunSummary]
