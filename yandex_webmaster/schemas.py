from datetime import datetime

from pydantic import BaseModel, Field


class AuthorizationRead(BaseModel):
    authorization_url: str


class ConnectionRead(BaseModel):
    connected: bool
    status: str
    selected_host_id: str | None = None
    selected_host_url: str | None = None
    last_checked_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None


class HostRead(BaseModel):
    host_id: str
    ascii_host_url: str
    unicode_host_url: str | None = None
    verified: bool = False


class HostSelection(BaseModel):
    host_id: str = Field(min_length=1, max_length=500)
    host_url: str = Field(min_length=1, max_length=500)


class QueryRead(BaseModel):
    query_id: str | None = None
    query_text: str
    indicators: dict[str, float | int | None] = Field(default_factory=dict)


class QueryFactRead(BaseModel):
    query: str
    url: str | None = None
    date: str | None = None
    impressions: float | None = None
    clicks: float | None = None
    ctr: float | None = None
    position: float | None = None
    demand: float | None = None


class WebmasterEvidenceRead(BaseModel):
    host_id: str
    host_url: str
    collected_at: datetime
    query_facts: list[QueryFactRead] = Field(default_factory=list)
    diagnostics: dict = Field(default_factory=dict)
    indexing: dict = Field(default_factory=dict)
    external_links: dict = Field(default_factory=dict)
    sitemaps: dict = Field(default_factory=dict)
    partial_errors: dict[str, str] = Field(default_factory=dict)
