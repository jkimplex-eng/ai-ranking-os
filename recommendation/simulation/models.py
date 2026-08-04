from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from recommendation.models import Recommendation


class RecommendationSimulation(Base):
    __tablename__ = "recommendation_simulations"
    __table_args__ = (
        Index(
            "ix_recommendation_simulations_recommendation_created",
            "recommendation_id",
            "created_at",
        ),
        CheckConstraint(
            "current_visibility >= 0 AND current_visibility <= 100",
            name="ck_recommendation_simulations_current_visibility",
        ),
        CheckConstraint(
            "predicted_visibility >= 0 AND predicted_visibility <= 100",
            name="ck_recommendation_simulations_predicted_visibility",
        ),
        CheckConstraint(
            "confidence_min <= confidence_expected "
            "AND confidence_expected <= confidence_max",
            name="ck_recommendation_simulations_confidence_order",
        ),
        CheckConstraint(
            "estimated_duration_days > 0",
            name="ck_recommendation_simulations_duration",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE")
    )
    current_visibility: Mapped[float] = mapped_column()
    predicted_visibility: Mapped[float] = mapped_column()
    predicted_delta: Mapped[float] = mapped_column()
    confidence_min: Mapped[float] = mapped_column()
    confidence_expected: Mapped[float] = mapped_column()
    confidence_max: Mapped[float] = mapped_column()
    estimated_duration_days: Mapped[int] = mapped_column(Integer)
    model_version: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    recommendation: Mapped[Recommendation] = relationship(
        back_populates="simulations"
    )
