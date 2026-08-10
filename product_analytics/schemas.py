from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from product_analytics.models import EventCategory


class AnalyticsPeriod(StrEnum):
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class StandardEvent(StrEnum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    REGISTER = "REGISTER"
    CREATE_RESEARCH = "CREATE_RESEARCH"
    START_RESEARCH = "START_RESEARCH"
    FINISH_RESEARCH = "FINISH_RESEARCH"
    CANCEL_RESEARCH = "CANCEL_RESEARCH"
    OPEN_REPORT = "OPEN_REPORT"
    EXPORT_REPORT = "EXPORT_REPORT"
    SUBMIT_FEEDBACK = "SUBMIT_FEEDBACK"
    UPDATE_SETTINGS = "UPDATE_SETTINGS"
    CREATE_ORGANIZATION = "CREATE_ORGANIZATION"
    INVITE_USER = "INVITE_USER"
    API_CALL = "API_CALL"
    ERROR = "ERROR"


class EventCreate(BaseModel):
    organization_id: int | None = Field(default=None, ge=1)
    user_id: int | None = Field(default=None, ge=1)
    session_id: str | None = Field(default=None, max_length=64)
    event_name: str = Field(min_length=1, max_length=100)
    event_category: EventCategory
    entity_type: str | None = Field(default=None, max_length=50)
    entity_id: str | None = Field(default=None, max_length=100)
    metadata: dict = Field(default_factory=dict)
    ip_hash: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=512)
    created_at: datetime | None = None


class EventRead(EventCreate):
    id: int
    created_at: datetime


class EventBatchCreate(BaseModel):
    events: list[EventCreate] = Field(min_length=1, max_length=1000)


class SessionStart(BaseModel):
    organization_id: int | None = Field(default=None, ge=1)
    device: str = Field(default="unknown", max_length=50)
    browser: str = Field(default="unknown", max_length=80)
    os: str = Field(default="unknown", max_length=80)


class SessionRead(BaseModel):
    id: str
    user_id: int | None
    organization_id: int | None
    started_at: datetime
    finished_at: datetime | None
    duration: float | None
    device: str
    browser: str
    os: str


class AnalyticsFilters(BaseModel):
    organization_id: int | None = None
    user_id: int | None = None
    provider: str | None = None
    template: str | None = None
    region: str | None = None
    language: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "AnalyticsFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
        return self


class DashboardRead(BaseModel):
    period: AnalyticsPeriod
    range_start: datetime
    range_end: datetime
    overview: dict
    users: dict
    organizations: dict
    sessions: dict
    research: dict
    reports: dict
    providers: dict
    feedback: dict
    errors: dict
    trends: list[dict]
    generated_at: datetime
    cached: bool = False
