from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.llm_router.schemas import RoutingProfile


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    settings: dict[str, Any] | None = None


class WorkspaceResearchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: str
    created_at: datetime
    progress_percent: float


class WorkspaceReportItem(BaseModel):
    research_id: int
    title: str
    visibility_score: float | None
    calculated_at: datetime | None


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    settings: dict[str, Any]
    recent_research: list[WorkspaceResearchItem]
    recent_reports: list[WorkspaceReportItem]
    favorite_projects: list[dict[str, Any]] = Field(default_factory=list)
    total_research: int
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10_000)
    settings: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list, max_length=50)
    favorite: bool = False


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    settings: dict[str, Any] | None = None
    tags: list[str] | None = Field(default=None, max_length=50)
    favorite: bool | None = None
    archived: bool | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str
    description: str
    settings: dict[str, Any]
    tags: list[str]
    favorite: bool
    archived: bool
    research_count: int = 0
    created_at: datetime
    updated_at: datetime


class CompetitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    domains: list[str] = Field(default_factory=list, max_length=100)
    brands: list[str] = Field(default_factory=list, max_length=100)
    notes: str = Field(default="", max_length=10_000)
    active: bool = True


class CompetitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    domains: list[str] | None = Field(default=None, max_length=100)
    brands: list[str] | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=10_000)
    active: bool | None = None


class CompetitorRead(CompetitorCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime


class CompetitorImport(BaseModel):
    competitors: list[CompetitorCreate] = Field(min_length=1, max_length=500)


class DomainCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=500)
    display_name: str | None = Field(default=None, max_length=253)
    is_primary: bool = False
    active: bool = True
    brands: list[str] = Field(default_factory=list, max_length=100)
    settings: dict[str, Any] = Field(default_factory=dict)


class DomainUpdate(BaseModel):
    hostname: str | None = Field(default=None, min_length=1, max_length=500)
    display_name: str | None = Field(default=None, min_length=1, max_length=253)
    is_primary: bool | None = None
    active: bool | None = None
    brands: list[str] | None = Field(default=None, max_length=100)
    settings: dict[str, Any] | None = None


class DomainRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    hostname: str
    display_name: str
    is_primary: bool
    active: bool
    brands: list[str]
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DomainImport(BaseModel):
    domains: list[DomainCreate] = Field(min_length=1, max_length=500)


class SavedConfigurationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    template_code: str = Field(default="ai-visibility", min_length=1, max_length=100)
    routing_profile: RoutingProfile = RoutingProfile.BALANCED
    languages: list[str] = Field(default_factory=lambda: ["ru"], min_length=1)
    regions: list[str] = Field(default_factory=lambda: ["GLOBAL"], min_length=1)
    prompt_count: int = Field(default=1, ge=1, le=100)
    schedule_hint: str | None = Field(default=None, max_length=100)
    configuration: dict[str, Any] = Field(default_factory=dict)


class SavedConfigurationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    template_code: str | None = Field(default=None, min_length=1, max_length=100)
    routing_profile: RoutingProfile | None = None
    languages: list[str] | None = Field(default=None, min_length=1)
    regions: list[str] | None = Field(default=None, min_length=1)
    prompt_count: int | None = Field(default=None, ge=1, le=100)
    schedule_hint: str | None = Field(default=None, max_length=100)
    configuration: dict[str, Any] | None = None


class SavedConfigurationRead(SavedConfigurationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime


class SavedConfigurationRunRequest(BaseModel):
    domain_id: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    query: str | None = Field(default=None, min_length=1, max_length=100_000)


class SavedConfigurationRunRead(BaseModel):
    research_id: int
    job_id: int
    state: str
