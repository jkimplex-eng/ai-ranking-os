from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scheduler.models import ScheduleExecutionStatus, ScheduleType


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=3)
    base_delay_seconds: float = Field(default=0, ge=0, le=300)


class ScheduleModel(BaseModel):
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)


class ScheduleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    research_id: int = Field(ge=1)
    schedule_type: ScheduleType
    cron_expression: str | None = Field(default=None, max_length=100)
    models: list[ScheduleModel] = Field(min_length=1, max_length=20)
    query: str | None = Field(default=None, min_length=1, max_length=100_000)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    is_enabled: bool = True
    start_at: datetime | None = None

    @model_validator(mode="after")
    def validate_cron(self) -> "ScheduleCreate":
        if (self.schedule_type == ScheduleType.CRON) != (self.cron_expression is not None):
            raise ValueError("cron_expression is required only for CRON schedules")
        return self


class ScheduleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    schedule_type: ScheduleType | None = None
    cron_expression: str | None = Field(default=None, max_length=100)
    models: list[ScheduleModel] | None = Field(default=None, min_length=1, max_length=20)
    query: str | None = Field(default=None, min_length=1, max_length=100_000)
    retry_policy: RetryPolicy | None = None
    is_enabled: bool | None = None


class ScheduleHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    attempt: int
    status: ScheduleExecutionStatus
    research_id: int | None
    error: str | None
    retry_delay_seconds: float
    started_at: datetime
    finished_at: datetime


class ScheduleExecutionRead(BaseModel):
    id: int
    schedule_id: int
    research_id: int | None
    status: ScheduleExecutionStatus
    attempts: int
    error: str | None
    scheduled_for: datetime
    started_at: datetime
    finished_at: datetime | None
    history: list[ScheduleHistoryRead]


class ScheduleRead(BaseModel):
    id: int
    name: str
    research_id: int
    schedule_type: ScheduleType
    cron_expression: str | None
    models: list[ScheduleModel]
    query: str | None
    retry_policy: RetryPolicy
    is_enabled: bool
    next_run_at: datetime
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

