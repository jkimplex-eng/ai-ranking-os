from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class AlertSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertType(StrEnum):
    VISIBILITY_DROP = "VISIBILITY_DROP"
    TREND_REVERSAL = "TREND_REVERSAL"
    BRAND_RECOMMENDATION_DISAPPEARED = "BRAND_RECOMMENDATION_DISAPPEARED"
    AUTHORITATIVE_CITATION_DISAPPEARED = "AUTHORITATIVE_CITATION_DISAPPEARED"
    CRITICAL_RECOMMENDATION_APPEARED = "CRITICAL_RECOMMENDATION_APPEARED"
    CONFIDENCE_SHOCK = "CONFIDENCE_SHOCK"


severity_type = Enum(
    AlertSeverity,
    name="alert_severity",
    native_enum=False,
    validate_strings=True,
    length=20,
)
alert_type = Enum(
    AlertType,
    name="alert_type",
    native_enum=False,
    validate_strings=True,
    length=60,
)


class AlertRule(Base):
    __tablename__ = "alert_rules"
    __table_args__ = (
        Index("uq_alert_rules_code_version", "code", "version", unique=True),
        Index("ix_alert_rules_active_version", "is_active", "version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    alert_type: Mapped[AlertType] = mapped_column(alert_type, nullable=False)
    threshold: Mapped[float | None] = mapped_column()
    severity: Mapped[AlertSeverity] = mapped_column(severity_type, nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="rule")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_entity_detected", "entity_id", "detected_at"),
        Index("ix_alerts_rule_id", "rule_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id"), nullable=False)
    alert_type: Mapped[AlertType] = mapped_column(alert_type, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(severity_type, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    previous_value: Mapped[float | None] = mapped_column()
    current_value: Mapped[float | None] = mapped_column()
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    rule: Mapped[AlertRule] = relationship(back_populates="alerts")
    events: Mapped[list["AlertEvent"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )


class AlertEvent(Base):
    __tablename__ = "alert_events"
    __table_args__ = (Index("ix_alert_events_alert_created", "alert_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    alert: Mapped[Alert] = relationship(back_populates="events")
