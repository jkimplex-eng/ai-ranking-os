from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class NotificationEventType(StrEnum):
    RESEARCH_COMPLETED = "RESEARCH_COMPLETED"
    RESEARCH_FAILED = "RESEARCH_FAILED"
    REPORT_READY = "REPORT_READY"
    ORGANIZATION_INVITATION = "ORGANIZATION_INVITATION"
    ROLE_CHANGED = "ROLE_CHANGED"
    FEEDBACK_PROCESSED = "FEEDBACK_PROCESSED"
    SYSTEM = "SYSTEM"
    SIGNIFICANT_CHANGE = "SIGNIFICANT_CHANGE"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    EXECUTION_FAILED = "EXECUTION_FAILED"


class NotificationCategory(StrEnum):
    RESEARCH = "RESEARCH"
    REPORT = "REPORT"
    ORGANIZATION = "ORGANIZATION"
    FEEDBACK = "FEEDBACK"
    SYSTEM = "SYSTEM"


class NotificationPriority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Notification(Base):
    __tablename__ = "product_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="SYSTEM")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(100))
    metadata_payload: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notification_id: Mapped[int] = mapped_column(
        ForeignKey("product_notifications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
