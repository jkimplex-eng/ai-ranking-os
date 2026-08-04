from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"
    __table_args__ = (Index("ix_benchmark_runs_calculated_id", "calculated_at", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False)
    metrics: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    entity_count: Mapped[int] = mapped_column(Integer, nullable=False)
    date_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    date_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    entries: Mapped[list["BenchmarkEntry"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class BenchmarkEntry(Base):
    __tablename__ = "benchmark_entries"
    __table_args__ = (
        Index("uq_benchmark_entries_run_entity", "run_id", "entity_id", unique=True),
        Index("ix_benchmark_entries_run_rank", "run_id", "overall_rank"),
        Index("ix_benchmark_entries_entity", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("benchmark_runs.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[str] = mapped_column(String(300), nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_results: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    overall_score: Mapped[float] = mapped_column(nullable=False)
    overall_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_percentile: Mapped[float] = mapped_column(nullable=False)
    run: Mapped[BenchmarkRun] = relationship(back_populates="entries")
