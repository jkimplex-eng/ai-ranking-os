from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class BaselineUpdatePolicy(StrEnum):
    MANUAL = "MANUAL"
    LATEST = "LATEST"
    BEST_VISIBILITY = "BEST_VISIBILITY"


class RegressionSeverity(StrEnum):
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"


policy_type = Enum(
    BaselineUpdatePolicy,
    name="baseline_update_policy",
    native_enum=False,
    validate_strings=True,
    length=30,
)
severity_type = Enum(
    RegressionSeverity,
    name="regression_severity",
    native_enum=False,
    validate_strings=True,
    length=20,
)


class Baseline(Base):
    __tablename__ = "baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[UUID] = mapped_column(Uuid, unique=True, nullable=False)
    research_id: Mapped[int] = mapped_column(Integer, nullable=False)
    update_policy: Mapped[BaselineUpdatePolicy] = mapped_column(policy_type, nullable=False)
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    snapshots: Mapped[list["BaselineSnapshot"]] = relationship(
        back_populates="baseline", cascade="all, delete-orphan"
    )
    events: Mapped[list["RegressionEvent"]] = relationship(
        back_populates="baseline", cascade="all, delete-orphan"
    )


class BaselineSnapshot(Base):
    __tablename__ = "baseline_snapshots"
    __table_args__ = (Index("ix_baseline_snapshots_baseline_created", "baseline_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    baseline_id: Mapped[int] = mapped_column(
        ForeignKey("baselines.id", ondelete="CASCADE"), nullable=False
    )
    research_id: Mapped[int] = mapped_column(Integer, nullable=False)
    visibility: Mapped[float] = mapped_column(nullable=False)
    mention: Mapped[float] = mapped_column(nullable=False)
    recommendation: Mapped[float] = mapped_column(nullable=False)
    citation: Mapped[float] = mapped_column(nullable=False)
    coverage: Mapped[float] = mapped_column(nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    baseline: Mapped[Baseline] = relationship(back_populates="snapshots")
    events: Mapped[list["RegressionEvent"]] = relationship(back_populates="snapshot")


class RegressionEvent(Base):
    __tablename__ = "regression_events"
    __table_args__ = (
        Index("ix_regression_events_baseline_created", "baseline_id", "created_at"),
        Index("ix_regression_events_snapshot_id", "baseline_snapshot_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    baseline_id: Mapped[int] = mapped_column(
        ForeignKey("baselines.id", ondelete="CASCADE"), nullable=False
    )
    baseline_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("baseline_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    current_research_id: Mapped[int] = mapped_column(Integer, nullable=False)
    metric: Mapped[str] = mapped_column(String(30), nullable=False)
    baseline_value: Mapped[float] = mapped_column(nullable=False)
    current_value: Mapped[float] = mapped_column(nullable=False)
    delta: Mapped[float] = mapped_column(nullable=False)
    severity: Mapped[RegressionSeverity] = mapped_column(severity_type, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    baseline: Mapped[Baseline] = relationship(back_populates="events")
    snapshot: Mapped[BaselineSnapshot] = relationship(back_populates="events")

