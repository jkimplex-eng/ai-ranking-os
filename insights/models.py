from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class InsightRun(Base):
    __tablename__ = "insight_runs"
    __table_args__ = (Index("ix_insight_runs_calculated_id", "calculated_at", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    insight_count: Mapped[int] = mapped_column(Integer, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    insights: Mapped[list["Insight"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class Insight(Base):
    __tablename__ = "insights"
    __table_args__ = (
        Index("ix_insights_run_type", "run_id", "insight_type"),
        Index("ix_insights_entity_metric", "entity_id", "metric"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("insight_runs.id", ondelete="CASCADE"), nullable=False
    )
    insight_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(300))
    metric: Mapped[str | None] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    previous_value: Mapped[float | None] = mapped_column()
    current_value: Mapped[float | None] = mapped_column()
    absolute_change: Mapped[float | None] = mapped_column()
    percentage_change: Mapped[float | None] = mapped_column()
    confidence: Mapped[float] = mapped_column(nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    recommendation: Mapped[str | None] = mapped_column(Text)
    run: Mapped[InsightRun] = relationship(back_populates="insights")
