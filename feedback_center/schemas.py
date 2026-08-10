from datetime import datetime

from pydantic import BaseModel, Field

from feedback_center.models import FeedbackPriority, FeedbackStatus, FeedbackType


class AttachmentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    storage_key: str = Field(min_length=1, max_length=500)
    size_bytes: int = Field(ge=0, le=50_000_000)
    metadata: dict = Field(default_factory=dict)


class FeedbackCreate(BaseModel):
    feedback_type: FeedbackType
    priority: FeedbackPriority = FeedbackPriority.MEDIUM
    title: str = Field(min_length=1, max_length=250)
    description: str = Field(min_length=1, max_length=50_000)
    project_id: int | None = Field(default=None, ge=1)
    research_id: int | None = Field(default=None, ge=1)
    report_id: int | None = Field(default=None, ge=1)
    organization_id: int | None = Field(default=None, ge=1)
    attachments: list[AttachmentCreate] = Field(default_factory=list, max_length=10)


class FeedbackAdminUpdate(BaseModel):
    status: FeedbackStatus | None = None
    priority: FeedbackPriority | None = None


class FeedbackBulkUpdate(FeedbackAdminUpdate):
    feedback_ids: list[int] = Field(min_length=1, max_length=500)


class AttachmentRead(BaseModel):
    id: int
    filename: str
    content_type: str
    storage_key: str
    size_bytes: int
    metadata: dict
    created_at: datetime


class FeedbackRead(BaseModel):
    id: int
    user_id: int
    feedback_type: FeedbackType
    priority: FeedbackPriority
    status: FeedbackStatus
    title: str
    description: str
    project_id: int | None
    research_id: int | None
    report_id: int | None
    organization_id: int | None
    attachments: list[AttachmentRead]
    created_at: datetime
    updated_at: datetime


class FeedbackHistoryRead(BaseModel):
    id: int
    feedback_id: int
    actor_id: str
    action: str
    old_state: dict | None
    new_state: dict | None
    created_at: datetime
