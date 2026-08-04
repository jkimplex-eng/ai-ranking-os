from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base

if TYPE_CHECKING:
    from recommendation.simulation.models import RecommendationSimulation
    from recommendation.templates.models import RecommendationTemplate


class RecommendationPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendationExecutionStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


priority_type = Enum(
    RecommendationPriority,
    name="recommendation_priority",
    native_enum=False,
    validate_strings=True,
    length=20,
)
execution_status_type = Enum(
    RecommendationExecutionStatus,
    name="recommendation_execution_status",
    native_enum=False,
    validate_strings=True,
    length=20,
)


class RecommendationRule(Base):
    __tablename__ = "recommendation_rules"
    __table_args__ = (
        Index(
            "ix_recommendation_rules_active_version",
            "is_active",
            "version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    recommendation_type: Mapped[str] = mapped_column(String(100))
    metric: Mapped[str] = mapped_column(String(100))
    operator: Mapped[str] = mapped_column(String(20), default="lt")
    threshold: Mapped[float] = mapped_column()
    priority: Mapped[RecommendationPriority] = mapped_column(priority_type)
    explanation_template: Mapped[str] = mapped_column(Text)
    expected_effect: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="rule"
    )


class RecommendationExecution(Base):
    __tablename__ = "recommendation_executions"
    __table_args__ = (
        Index(
            "ix_recommendation_executions_research_started",
            "research_id",
            "started_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    research_id: Mapped[int] = mapped_column(Integer)
    status: Mapped[RecommendationExecutionStatus] = mapped_column(
        execution_status_type,
        default=RecommendationExecutionStatus.RUNNING,
    )
    engine_version: Mapped[str] = mapped_column(String(50))
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    generated_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
    )


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index("ix_recommendations_research_created", "research_id", "created_at"),
        Index("ix_recommendations_execution_priority", "execution_id", "priority"),
        Index("ix_recommendations_rule_id", "rule_id"),
        Index("ix_recommendations_template_id", "template_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("recommendation_executions.id", ondelete="CASCADE")
    )
    rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("recommendation_rules.id", ondelete="SET NULL")
    )
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("recommendation_templates.id", ondelete="SET NULL")
    )
    research_id: Mapped[int] = mapped_column(Integer)
    recommendation_type: Mapped[str] = mapped_column(String(100))
    priority: Mapped[RecommendationPriority] = mapped_column(priority_type)
    explanation: Mapped[str] = mapped_column(Text)
    metric: Mapped[str] = mapped_column(String(100))
    metric_value: Mapped[float] = mapped_column()
    expected_effect: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    execution: Mapped[RecommendationExecution] = relationship(
        back_populates="recommendations"
    )
    rule: Mapped[RecommendationRule | None] = relationship(
        back_populates="recommendations"
    )
    template: Mapped["RecommendationTemplate | None"] = relationship(
        back_populates="recommendations"
    )
    simulations: Mapped[list["RecommendationSimulation"]] = relationship(
        back_populates="recommendation",
        cascade="all, delete-orphan",
    )
