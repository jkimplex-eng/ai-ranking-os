from datetime import datetime

from pydantic import BaseModel, Field


class ConnectionCreate(BaseModel):
    api_key: str = Field(min_length=8, max_length=4096)
    provider_hint: str | None = Field(default=None, max_length=50)
    folder_id: str | None = Field(default=None, min_length=8, max_length=100)
    organization_id: int | None = None
    free_only: bool = True


class ConnectionRead(BaseModel):
    id: int
    organization_id: int
    provider: str
    display_name: str
    masked_key: str
    status: str
    free_only: bool
    paid_fallback: bool
    last_checked_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    created_at: datetime


class ConnectionTestRead(BaseModel):
    provider: str
    status: str
    latency_ms: int
    models: list[str]
    free_models: list[str]
    checked_at: datetime
