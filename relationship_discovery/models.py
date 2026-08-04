from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class RelationshipType(StrEnum):
    MENTIONS = "MENTIONS"
    RECOMMENDS = "RECOMMENDS"
    REFERENCES = "REFERENCES"
    COMPETES_WITH = "COMPETES_WITH"
    RELATED_TO = "RELATED_TO"
    BELONGS_TO = "BELONGS_TO"
    PRODUCES = "PRODUCES"
    CREATED_BY = "CREATED_BY"


class RelationshipStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RelationshipDecisionType(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


relationship_type = Enum(
    RelationshipType,
    name="discovered_relationship_type",
    native_enum=False,
    validate_strings=True,
    length=30,
)
status_type = Enum(
    RelationshipStatus,
    name="relationship_candidate_status",
    native_enum=False,
    validate_strings=True,
    length=20,
)
decision_type = Enum(
    RelationshipDecisionType,
    name="relationship_decision_type",
    native_enum=False,
    validate_strings=True,
    length=20,
)


class RelationshipCandidate(Base):
    __tablename__ = "relationship_candidates"
    __table_args__ = (
        Index(
            "uq_relationship_candidates_identity",
            "graph_snapshot_id",
            "source_external_id",
            "target_external_id",
            "relationship_type",
            unique=True,
        ),
        Index("ix_relationship_candidates_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    graph_snapshot_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_external_id: Mapped[str] = mapped_column(String(300), nullable=False)
    target_external_id: Mapped[str] = mapped_column(String(300), nullable=False)
    relationship_type: Mapped[RelationshipType] = mapped_column(relationship_type, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[RelationshipStatus] = mapped_column(status_type, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    integrated_snapshot_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence: Mapped[list["RelationshipEvidence"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["RelationshipDecision"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class RelationshipEvidence(Base):
    __tablename__ = "relationship_evidence"
    __table_args__ = (
        Index("ix_relationship_evidence_candidate", "candidate_id"),
        Index(
            "uq_relationship_evidence_source",
            "candidate_id",
            "source_type",
            "source_reference",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("relationship_candidates.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(300), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    candidate: Mapped[RelationshipCandidate] = relationship(back_populates="evidence")


class RelationshipDecision(Base):
    __tablename__ = "relationship_decisions"
    __table_args__ = (
        Index("ix_relationship_decisions_candidate_created", "candidate_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("relationship_candidates.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[RelationshipDecisionType] = mapped_column(decision_type, nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    candidate: Mapped[RelationshipCandidate] = relationship(back_populates="decisions")
