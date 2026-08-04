from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class LinkStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LinkDecisionType(StrEnum):
    AUTO_CREATE = "AUTO_CREATE"
    AUTO_MATCH = "AUTO_MATCH"
    MANUAL_APPROVE = "MANUAL_APPROVE"
    MANUAL_REJECT = "MANUAL_REJECT"


status_type = Enum(
    LinkStatus, name="link_status", native_enum=False, validate_strings=True, length=20
)
decision_type = Enum(
    LinkDecisionType,
    name="link_decision_type",
    native_enum=False,
    validate_strings=True,
    length=30,
)


class CanonicalEntity(Base):
    __tablename__ = "canonical_entities"
    __table_args__ = (
        Index(
            "uq_canonical_entities_type_normalized",
            "entity_type",
            "normalized_name",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    aliases: Mapped[list["EntityAlias"]] = relationship(
        back_populates="canonical_entity", cascade="all, delete-orphan"
    )
    candidates: Mapped[list["LinkCandidate"]] = relationship(back_populates="canonical_entity")


class EntityAlias(Base):
    __tablename__ = "entity_aliases"
    __table_args__ = (
        Index("uq_entity_aliases_type_normalized", "entity_type", "normalized_alias", unique=True),
        Index("ix_entity_aliases_canonical_id", "canonical_entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_entity_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_entities.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    canonical_entity: Mapped[CanonicalEntity] = relationship(back_populates="aliases")


class LinkCandidate(Base):
    __tablename__ = "link_candidates"
    __table_args__ = (
        Index("ix_link_candidates_status_created", "status", "created_at"),
        Index("ix_link_candidates_snapshot_node", "graph_snapshot_id", "graph_node_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    graph_snapshot_id: Mapped[int] = mapped_column(Integer, nullable=False)
    graph_node_id: Mapped[int] = mapped_column(Integer, nullable=False)
    external_id: Mapped[str] = mapped_column(String(300), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_entity_id: Mapped[int | None] = mapped_column(
        ForeignKey("canonical_entities.id", ondelete="SET NULL")
    )
    confidence: Mapped[float] = mapped_column(nullable=False)
    match_method: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[LinkStatus] = mapped_column(status_type, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canonical_entity: Mapped[CanonicalEntity | None] = relationship(back_populates="candidates")
    decisions: Mapped[list["LinkDecision"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class LinkDecision(Base):
    __tablename__ = "link_decisions"
    __table_args__ = (Index("ix_link_decisions_candidate_created", "candidate_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("link_candidates.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[LinkDecisionType] = mapped_column(decision_type, nullable=False)
    canonical_entity_id: Mapped[int | None] = mapped_column(Integer)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    candidate: Mapped[LinkCandidate] = relationship(back_populates="decisions")
