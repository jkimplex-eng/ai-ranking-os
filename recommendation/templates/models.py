from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from recommendation.models import Recommendation, RecommendationPriority, priority_type


class RecommendationTemplate(Base):
    __tablename__ = "recommendation_templates"
    __table_args__ = (
        UniqueConstraint(
            "template_code",
            "version",
            name="uq_recommendation_templates_code_version",
        ),
        Index(
            "ix_recommendation_templates_type_version",
            "recommendation_type",
            "version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_code: Mapped[str] = mapped_column(String(100))
    recommendation_type: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    steps: Mapped[list[str]] = mapped_column(JSON)
    expected_result: Mapped[str] = mapped_column(Text)
    estimated_time: Mapped[str] = mapped_column(String(100))
    priority: Mapped[RecommendationPriority] = mapped_column(priority_type)
    version: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    recommendations: Mapped[list[Recommendation]] = relationship(
        back_populates="template"
    )
