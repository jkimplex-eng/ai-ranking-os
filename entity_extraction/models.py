from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class EntityExtractionRun(Base):
    __tablename__ = "entity_extraction_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    model: Mapped[str | None] = mapped_column(String(100))
    raw_response: Mapped[Any] = mapped_column(JSON)
    output_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    version: Mapped[str] = mapped_column(String(50))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class EntityHistory(Base):
    __tablename__ = "entity_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("entity_extraction_runs.id", ondelete="CASCADE"))
    response_id: Mapped[str] = mapped_column(String(200), index=True)
    entity_id: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(500))
    canonical_name: Mapped[str] = mapped_column(String(500), index=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    aliases: Mapped[list[str]] = mapped_column(JSON)
    knowledge_graph_id: Mapped[str] = mapped_column(String(100), index=True)


class RelationHistory(Base):
    __tablename__ = "relation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("entity_extraction_runs.id", ondelete="CASCADE"))
    response_id: Mapped[str] = mapped_column(String(200), index=True)
    relation_id: Mapped[str] = mapped_column(String(100))
    source_entity_id: Mapped[str] = mapped_column(String(100))
    target_entity_id: Mapped[str] = mapped_column(String(100))
    relation_type: Mapped[str] = mapped_column(String(50), index=True)
    confidence: Mapped[float] = mapped_column(Float)


class ResolutionLogHistory(Base):
    __tablename__ = "resolution_log_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("entity_extraction_runs.id", ondelete="CASCADE"))
    response_id: Mapped[str] = mapped_column(String(200), index=True)
    stage: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict[str, Any]] = mapped_column(JSON)
    message: Mapped[str | None] = mapped_column(Text)

