from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class ResearchPublication(Base):
    __tablename__ = "research_publications"
    __table_args__ = (
        Index("ix_research_publications_entity_published", "entity_id", "published_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    research_id: Mapped[int | None] = mapped_column(
        ForeignKey("researches.id", ondelete="SET NULL"), index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False, default="OWNED")
    content_type: Mapped[str] = mapped_column(String(80), nullable=False, default="ARTICLE")
    topic: Mapped[str | None] = mapped_column(String(500))
    target_queries: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    observations: Mapped[list["PublicationObservation"]] = relationship(
        back_populates="publication", cascade="all, delete-orphan"
    )


class PublicationObservation(Base):
    __tablename__ = "publication_observations"
    __table_args__ = (
        Index(
            "uq_publication_observation_provider_model",
            "publication_id",
            "provider",
            "model",
            unique=True,
        ),
        Index("ix_publication_observations_first_observed", "first_observed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    publication_id: Mapped[int] = mapped_column(
        ForeignKey("research_publications.id", ondelete="CASCADE"), nullable=False
    )
    research_id: Mapped[int] = mapped_column(
        ForeignKey("researches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    response_id: Mapped[int] = mapped_column(
        ForeignKey("research_responses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    publication: Mapped[ResearchPublication] = relationship(back_populates="observations")
