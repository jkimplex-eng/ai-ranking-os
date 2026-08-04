from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class TrendDirection(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    STABLE = "STABLE"


trend_direction_type = Enum(
    TrendDirection,
    name="trend_direction",
    native_enum=False,
    validate_strings=True,
    length=10,
)


class TrendSeries(Base):
    __tablename__ = "trend_series"
    __table_args__ = (
        Index("uq_trend_series_entity_version", "entity_id", "model_version", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    moving_average_window: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    snapshots: Mapped[list["TrendSnapshot"]] = relationship(
        back_populates="series", cascade="all, delete-orphan"
    )


class TrendSnapshot(Base):
    __tablename__ = "trend_snapshots"
    __table_args__ = (Index("ix_trend_snapshots_series_built", "series_id", "built_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(
        ForeignKey("trend_series.id", ondelete="CASCADE"), nullable=False
    )
    source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    built_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    series: Mapped[TrendSeries] = relationship(back_populates="snapshots")
    points: Mapped[list["TrendPoint"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class TrendPoint(Base):
    __tablename__ = "trend_points"
    __table_args__ = (
        Index("ix_trend_points_snapshot_metric_time", "snapshot_id", "metric", "observed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("trend_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    research_id: Mapped[int] = mapped_column(Integer, nullable=False)
    metric: Mapped[str] = mapped_column(String(30), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(nullable=False)
    moving_average: Mapped[float] = mapped_column(nullable=False)
    percentage_change: Mapped[float | None] = mapped_column()
    direction: Mapped[TrendDirection] = mapped_column(trend_direction_type, nullable=False)
    snapshot: Mapped[TrendSnapshot] = relationship(back_populates="points")

