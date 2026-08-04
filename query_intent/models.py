from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class IntentClassificationRun(Base):
    __tablename__ = "intent_classification_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    query: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(20), index=True)
    primary_intent: Mapped[str] = mapped_column(String(50), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    output_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    version: Mapped[str] = mapped_column(String(50))
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class IntentHistory(Base):
    __tablename__ = "intent_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("intent_classification_runs.id", ondelete="CASCADE")
    )
    request_id: Mapped[str] = mapped_column(String(200), index=True)
    intent: Mapped[str] = mapped_column(String(50), index=True)
    subtype: Mapped[str] = mapped_column(String(100))
    confidence: Mapped[float] = mapped_column(Float)
    is_primary: Mapped[bool] = mapped_column(Boolean)
    signals: Mapped[list[str]] = mapped_column(JSON)


class ConfidenceHistory(Base):
    __tablename__ = "confidence_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("intent_classification_runs.id", ondelete="CASCADE")
    )
    request_id: Mapped[str] = mapped_column(String(200), index=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    intent: Mapped[str] = mapped_column(String(50), index=True)
    confidence: Mapped[float] = mapped_column(Float)


class RoutingMetadataHistory(Base):
    __tablename__ = "routing_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("intent_classification_runs.id", ondelete="CASCADE")
    )
    request_id: Mapped[str] = mapped_column(String(200), index=True)
    strategy: Mapped[str] = mapped_column(String(100), index=True)
    llm_fallback_required: Mapped[bool] = mapped_column(Boolean)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
