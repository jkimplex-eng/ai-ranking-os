from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from analytics.schemas import AnalyticsFilter


class SegmentType(StrEnum):
    BRAND = "BRAND"
    CATEGORY = "CATEGORY"
    COUNTRY = "COUNTRY"
    MARKETPLACE = "MARKETPLACE"
    SOURCE = "SOURCE"
    LANGUAGE = "LANGUAGE"
    MODEL = "MODEL"
    CUSTOM = "CUSTOM"

    @property
    def dimension(self) -> str | None:
        return None if self is SegmentType.CUSTOM else self.value.casefold()


class SegmentCreate(BaseModel):
    code: str = Field(min_length=2, max_length=100, pattern=r"^[a-z][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=200)
    segment_type: SegmentType
    rules: list[AnalyticsFilter] = Field(min_length=1, max_length=50)
    version: str = Field(default="1.0", min_length=1, max_length=50)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_builtin_dimension(self) -> "SegmentCreate":
        dimension = self.segment_type.dimension
        if dimension and not any(rule.field == dimension for rule in self.rules):
            raise ValueError(f"{self.segment_type.value} segment requires a {dimension!r} rule")
        return self


class SegmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    rules: list[AnalyticsFilter] | None = Field(default=None, min_length=1, max_length=50)
    version: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None


class SegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    segment_type: SegmentType
    rules: list[AnalyticsFilter]
    version: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SegmentPage(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    items: list[SegmentRead]


class SegmentMemberRead(BaseModel):
    member_key: str
    observed_at: datetime
    dimensions: dict[str, str]
    metrics: dict[str, float]


class SegmentEvaluationRead(BaseModel):
    id: int
    segment_id: int
    segment_code: str
    segment_version: str
    source_count: int = Field(ge=0)
    matched_count: int = Field(ge=0)
    evaluated_at: datetime
    members: list[SegmentMemberRead]


class SegmentTypeRead(BaseModel):
    type: SegmentType
    dimension: str | None
    custom: bool
