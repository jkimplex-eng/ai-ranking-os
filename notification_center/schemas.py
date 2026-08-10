from datetime import datetime

from pydantic import BaseModel, Field

from notification_center.models import (
    NotificationCategory,
    NotificationEventType,
    NotificationPriority,
)


class NotificationEventCreate(BaseModel):
    event_type: NotificationEventType
    category: NotificationCategory = NotificationCategory.SYSTEM
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str = Field(min_length=1, max_length=250)
    message: str = Field(min_length=1, max_length=10_000)
    resource_type: str | None = Field(default=None, max_length=50)
    resource_id: str | None = Field(default=None, max_length=100)
    metadata: dict = Field(default_factory=dict)
    channels: list[str] = Field(default_factory=lambda: ["UI"])


class DeliveryRead(BaseModel):
    id: int
    channel: str
    status: str
    attempts: int
    error: str | None


class NotificationRead(BaseModel):
    id: int
    user_id: int
    event_type: NotificationEventType
    category: NotificationCategory
    priority: NotificationPriority
    title: str
    message: str
    resource_type: str | None
    resource_id: str | None
    metadata: dict
    is_read: bool
    read_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    deliveries: list[DeliveryRead]


class NotificationSummary(BaseModel):
    unread: int
    total: int
    archived: int
