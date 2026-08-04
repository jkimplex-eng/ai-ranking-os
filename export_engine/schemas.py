from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from analytics.schemas import AnalyticsFilter


class ExportFormat(StrEnum):
    CSV = "CSV"
    XLSX = "XLSX"
    JSON = "JSON"
    PARQUET = "PARQUET"


class ExportRequest(BaseModel):
    analytics_run_ids: list[int] = Field(min_length=1, max_length=1000)
    format: ExportFormat
    filters: list[AnalyticsFilter] = Field(default_factory=list, max_length=50)
    columns: list[str] = Field(default_factory=list, max_length=500)
    batch_size: int = Field(default=1000, ge=1, le=10000)
    filename: str = Field(default="analytics-export", pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$")

    @model_validator(mode="after")
    def validate_unique_values(self) -> "ExportRequest":
        if len(set(self.analytics_run_ids)) != len(self.analytics_run_ids):
            raise ValueError("analytics_run_ids must be unique")
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("columns must be unique")
        return self


class ExportDescriptor(BaseModel):
    media_type: str
    extension: str
    row_count: int = Field(ge=0)
    columns: list[str]
