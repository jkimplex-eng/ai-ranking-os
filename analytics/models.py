from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class AnalyticsRun(Base):
    __tablename__ = "analytics_runs"
    __table_args__ = (
        Index("ix_analytics_runs_calculated_id", "calculated_at", "id"),
        Index("ix_analytics_runs_version_calculated", "engine_version", "calculated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False)
    query_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    group_count: Mapped[int] = mapped_column(Integer, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
