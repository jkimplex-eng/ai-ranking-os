from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class TimeInterval(StrEnum):
    NONE = "NONE"
    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"


class FilterOperator(StrEnum):
    EQ = "EQ"
    NE = "NE"
    IN = "IN"
    NOT_IN = "NOT_IN"
    CONTAINS = "CONTAINS"
    GTE = "GTE"
    LTE = "LTE"


class Statistic(StrEnum):
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    MEDIAN = "MEDIAN"
    STDDEV = "STDDEV"
    P25 = "P25"
    P75 = "P75"
    P90 = "P90"
    P95 = "P95"


FilterValue = str | float | int | bool | list[str] | list[float] | list[int]


class AnalyticsFilter(BaseModel):
    field: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")
    operator: FilterOperator = FilterOperator.EQ
    value: FilterValue


class AnalyticsQuery(BaseModel):
    metrics: list[str] = Field(min_length=1, max_length=50)
    group_by: list[str] = Field(default_factory=list, max_length=10)
    filters: list[AnalyticsFilter] = Field(default_factory=list, max_length=50)
    interval: TimeInterval = TimeInterval.NONE
    statistics: list[Statistic] = Field(
        default_factory=lambda: [
            Statistic.COUNT,
            Statistic.AVG,
            Statistic.MIN,
            Statistic.MAX,
        ],
        min_length=1,
    )
    date_from: datetime | None = None
    date_to: datetime | None = None

    @model_validator(mode="after")
    def validate_query(self) -> "AnalyticsQuery":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("metrics must be unique")
        if len(set(self.group_by)) != len(self.group_by):
            raise ValueError("group_by fields must be unique")
        if len(set(self.statistics)) != len(self.statistics):
            raise ValueError("statistics must be unique")
        return self


class MetricStatistics(BaseModel):
    values: dict[Statistic, float | int]


class AnalyticsGroup(BaseModel):
    dimensions: dict[str, str]
    interval_start: datetime | None
    record_count: int = Field(ge=0)
    metrics: dict[str, MetricStatistics]


class AnalyticsResult(BaseModel):
    run_id: int
    engine_version: str
    source_record_count: int = Field(ge=0)
    group_count: int = Field(ge=0)
    query: AnalyticsQuery
    groups: list[AnalyticsGroup]
    calculated_at: datetime


class AnalyticsRunSummary(BaseModel):
    id: int
    engine_version: str
    source_record_count: int = Field(ge=0)
    group_count: int = Field(ge=0)
    calculated_at: datetime


class AnalyticsRunPage(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    items: list[AnalyticsRunSummary]


class StoredAnalyticsRun(BaseModel):
    id: int
    engine_version: str
    query_payload: dict[str, Any]
    result_payload: dict[str, Any]
    source_record_count: int
    group_count: int
    calculated_at: datetime
