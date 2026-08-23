from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class AliceObservation(Base):
    __tablename__ = "alice_learning_observations"
    __table_args__ = (
        Index(
            "uq_alice_learning_response_version",
            "response_id",
            "feature_version",
            unique=True,
        ),
        Index(
            "ix_alice_learning_org_category_observed",
            "organization_id",
            "category",
            "observed_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    research_id: Mapped[int] = mapped_column(
        ForeignKey("researches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    response_id: Mapped[int] = mapped_column(
        ForeignKey("research_responses.id", ondelete="CASCADE"), nullable=False
    )
    brand: Mapped[str] = mapped_column(String(300), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="UNIVERSAL")
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="ru")
    region: Mapped[str] = mapped_column(String(20), nullable=False, default="RU")
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    mentioned: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recommended: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cited: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recommendation_rank: Mapped[int | None] = mapped_column(Integer)
    source_domains: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    feature_evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    evidence_status: Mapped[str] = mapped_column(String(30), nullable=False)
    feature_version: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class AliceModelSnapshot(Base):
    __tablename__ = "alice_learning_models"
    __table_args__ = (
        Index(
            "ix_alice_learning_model_dimension",
            "organization_id",
            "category",
            "language",
            "region",
            "trained_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    region: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    model_type: Mapped[str] = mapped_column(String(80), nullable=False)
    intercept: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    coefficients: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    feature_statistics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    positive_samples: Mapped[int] = mapped_column(Integer, nullable=False)
    negative_samples: Mapped[int] = mapped_column(Integer, nullable=False)
    validation: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    limitations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    algorithm_version: Mapped[str] = mapped_column(String(20), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class AlicePrediction(Base):
    __tablename__ = "alice_learning_predictions"
    __table_args__ = (
        Index("ix_alice_learning_prediction_org_created", "organization_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_id: Mapped[int] = mapped_column(
        ForeignKey("alice_learning_models.id", ondelete="CASCADE"), nullable=False
    )
    brand: Mapped[str] = mapped_column(String(300), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    features: Mapped[dict] = mapped_column(JSON, nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    counterfactuals: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    explanation: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    evidence_status: Mapped[str] = mapped_column(String(30), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
