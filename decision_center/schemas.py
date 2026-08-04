from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decision_center.models import AgentType, TaskPriority, TaskStatus


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    status: TaskStatus = TaskStatus.BACKLOG
    priority: TaskPriority = TaskPriority.MEDIUM
    required_specialization: str | None = Field(default=None, max_length=100)
    owner_id: int | None = Field(default=None, ge=1)
    sprint_id: int | None = Field(default=None, ge=1)
    project_id: int | None = Field(default=None, ge=1)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    required_specialization: str | None = Field(default=None, max_length=100)
    sprint_id: int | None = Field(default=None, ge=1)
    project_id: int | None = Field(default=None, ge=1)


class TaskAssign(BaseModel):
    agent_id: int = Field(ge=1)


class TaskRead(ApiModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    required_specialization: str | None
    owner_id: int | None
    sprint_id: int | None
    project_id: int | None
    created_at: datetime
    updated_at: datetime


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    agent_type: AgentType = AgentType.CODEX
    specialization: str | None = Field(default=None, max_length=100)
    is_enabled: bool = True


class AgentRead(ApiModel):
    id: int
    name: str
    description: str | None
    agent_type: AgentType
    specialization: str | None
    is_enabled: bool
    created_at: datetime


class SprintCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    goal: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    project_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_dates(self) -> "SprintCreate":
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must be on or after starts_on")
        return self


class SprintRead(ApiModel):
    id: int
    name: str
    goal: str | None
    starts_on: date | None
    ends_on: date | None
    project_id: int | None
    created_at: datetime
