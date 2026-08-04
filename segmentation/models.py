from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class SegmentDefinition(Base):
    __tablename__ = "segment_definitions"
    __table_args__ = (
        Index("uq_segment_definitions_code", "code", unique=True),
        Index("ix_segment_definitions_type_active", "segment_type", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    segment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    evaluations: Mapped[list["SegmentEvaluation"]] = relationship(
        back_populates="segment", cascade="all, delete-orphan"
    )


class SegmentEvaluation(Base):
    __tablename__ = "segment_evaluations"
    __table_args__ = (Index("ix_segment_evaluations_segment_time", "segment_id", "evaluated_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    segment_id: Mapped[int] = mapped_column(
        ForeignKey("segment_definitions.id", ondelete="CASCADE"), nullable=False
    )
    segment_version: Mapped[str] = mapped_column(String(50), nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    segment: Mapped[SegmentDefinition] = relationship(back_populates="evaluations")
    memberships: Mapped[list["SegmentMembership"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )


class SegmentMembership(Base):
    __tablename__ = "segment_memberships"
    __table_args__ = (
        Index("uq_segment_memberships_evaluation_key", "evaluation_id", "member_key", unique=True),
        Index("ix_segment_memberships_key", "member_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(
        ForeignKey("segment_evaluations.id", ondelete="CASCADE"), nullable=False
    )
    member_key: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dimensions: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    evaluation: Mapped[SegmentEvaluation] = relationship(back_populates="memberships")
