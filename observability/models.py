from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class TraceSpan(Base):
    __tablename__ = "observability_spans"
    __table_args__ = (Index("ix_spans_trace_started", "trace_id", "started_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    span_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    operation: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
