from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class EventCategory(StrEnum):
    AUTHENTICATION = "AUTHENTICATION"
    NAVIGATION = "NAVIGATION"
    RESEARCH = "RESEARCH"
    REPORT = "REPORT"
    FEEDBACK = "FEEDBACK"
    ORGANIZATION = "ORGANIZATION"
    SETTINGS = "SETTINGS"
    ADMINISTRATION = "ADMINISTRATION"
    API = "API"
    ERROR = "ERROR"


class AnalyticsEvent(Base):
    __tablename__ = "product_analytics_events"
    __table_args__ = (
        Index("ix_product_analytics_event_time_category", "created_at", "event_category"),
        Index("ix_product_analytics_event_org_time", "organization_id", "created_at"),
        Index("ix_product_analytics_event_user_time", "user_id", "created_at"),
        Index("ix_product_analytics_event_name_time", "event_name", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(Integer)
    user_id: Mapped[int | None] = mapped_column(Integer)
    session_id: Mapped[str | None] = mapped_column(String(64))
    event_name: Mapped[str] = mapped_column(String(100), nullable=False)
    event_category: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(100))
    metadata_payload: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class AnalyticsSession(Base):
    __tablename__ = "product_analytics_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    organization_id: Mapped[int | None] = mapped_column(Integer, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration: Mapped[float | None] = mapped_column(Float)
    device: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    browser: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown")
    os: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown")


class AnalyticsReport(Base):
    __tablename__ = "product_analytics_reports"
    __table_args__ = (Index("ix_product_analytics_report_period", "period", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    filters_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    range_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    range_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
