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


class AliceAutomationPlan(Base):
    __tablename__ = "alice_automation_plans"
    __table_args__ = (
        Index("ix_alice_automation_due", "is_enabled", "next_run_at"),
        Index("ix_alice_automation_org_brand", "organization_id", "brand"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    template_research_id: Mapped[int] = mapped_column(
        ForeignKey("researches.id", ondelete="CASCADE"), nullable=False
    )
    brand: Mapped[str] = mapped_column(String(300), nullable=False)
    website_url: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="ru")
    region: Mapped[str] = mapped_column(String(20), nullable=False, default="RU")
    research_profile: Mapped[str] = mapped_column(String(40), nullable=False, default="UNIVERSAL")
    routing_profile: Mapped[str] = mapped_column(String(40), nullable=False, default="BALANCED")
    models: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    daily_query_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    weekly_query_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    daily_budget_usd: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    monthly_budget_usd: Mapped[float] = mapped_column(Float, nullable=False, default=30.0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class AliceQuerySet(Base):
    __tablename__ = "alice_automation_query_sets"
    __table_args__ = (
        Index("uq_alice_query_set_version", "plan_id", "version", "kind", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("alice_automation_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    queries: Mapped[list] = mapped_column(JSON, nullable=False)
    source_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class AliceAutomationRun(Base):
    __tablename__ = "alice_automation_runs"
    __table_args__ = (
        Index("ix_alice_automation_run_plan_started", "plan_id", "started_at"),
        Index(
            "uq_alice_automation_one_running",
            "plan_id",
            unique=True,
            postgresql_where=text("status = 'RUNNING'"),
            sqlite_where=text("status = 'RUNNING'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("alice_automation_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query_set_id: Mapped[int] = mapped_column(
        ForeignKey("alice_automation_query_sets.id", ondelete="RESTRICT"), nullable=False
    )
    run_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    research_id: Mapped[int | None] = mapped_column(
        ForeignKey("researches.id", ondelete="SET NULL")
    )
    task_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost_usd: Mapped[float | None] = mapped_column(Float)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
