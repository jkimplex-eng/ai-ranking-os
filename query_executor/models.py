from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class QueryExecutionHistory(Base):
    __tablename__ = "query_execution_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    plan_id: Mapped[str] = mapped_column(String(200), index=True)
    request_id: Mapped[str | None] = mapped_column(String(200), index=True)
    mode: Mapped[str] = mapped_column(String(30), index=True)
    state: Mapped[str] = mapped_column(String(30), index=True)
    plan_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    output_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class QueryExecutionMetric(Base):
    __tablename__ = "query_execution_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_row_id: Mapped[int] = mapped_column(
        ForeignKey("query_execution_history.id", ondelete="CASCADE")
    )
    execution_id: Mapped[str] = mapped_column(String(200), index=True)
    metric_name: Mapped[str] = mapped_column(String(100), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(30))
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class QueryProviderMetric(Base):
    __tablename__ = "query_provider_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_row_id: Mapped[int] = mapped_column(
        ForeignKey("query_execution_history.id", ondelete="CASCADE")
    )
    execution_id: Mapped[str] = mapped_column(String(200), index=True)
    step_id: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[str] = mapped_column(String(30), index=True)
    attempts: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer)
    failure: Mapped[str | None] = mapped_column(Text)

