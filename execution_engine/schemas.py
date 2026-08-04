from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from decision_center.models import TaskPriority
from execution_engine.models import ExecutionState


class ExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    agent_id: int | None
    state: ExecutionState
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    result: dict[str, Any] | None
    error: str | None
    attempt_count: int
    created_at: datetime


class ExecutionCancel(BaseModel):
    execution_id: int = Field(ge=1)


class QueueTaskRead(BaseModel):
    id: int
    title: str
    priority: TaskPriority
    required_specialization: str | None
    created_at: datetime

