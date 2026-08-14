from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class PublicationExperiment(Base):
    __tablename__ = "publication_learning_experiments"
    __table_args__ = (
        Index(
            "uq_publication_learning_experiment",
            "publication_id",
            "followup_research_id",
            "algorithm_version",
            unique=True,
        ),
        Index("ix_publication_learning_entity_evaluated", "entity_id", "evaluated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    publication_id: Mapped[int] = mapped_column(
        ForeignKey("research_publications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    baseline_research_id: Mapped[int] = mapped_column(
        ForeignKey("researches.id", ondelete="CASCADE"), nullable=False
    )
    followup_research_id: Mapped[int] = mapped_column(
        ForeignKey("researches.id", ondelete="CASCADE"), nullable=False
    )
    matrix_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    causality_status: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_grade: Mapped[str] = mapped_column(String(20), nullable=False)
    metric_deltas: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    provider_deltas: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(20), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class PublicationInfluenceEstimate(Base):
    __tablename__ = "publication_influence_estimates"
    __table_args__ = (
        Index(
            "uq_publication_influence_dimension",
            "resource_domain",
            "channel",
            "content_type",
            "metric",
            "provider",
            "model",
            "category",
            "language",
            "region",
            "algorithm_version",
            unique=True,
        ),
        Index("ix_publication_influence_rank", "metric", "expected_delta", "confidence_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    content_type: Mapped[str] = mapped_column(String(80), nullable=False)
    metric: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, default="ALL")
    model: Mapped[str] = mapped_column(String(200), nullable=False, default="ALL")
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="UNIVERSAL")
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="ALL")
    region: Mapped[str] = mapped_column(String(20), nullable=False, default="ALL")
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_delta: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_min: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_max: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_grade: Mapped[str] = mapped_column(String(20), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
