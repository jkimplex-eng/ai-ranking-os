from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class EISScore(Base):
    __tablename__ = "eis_scores"
    __table_args__ = (
        Index("ix_eis_scores_platform_calculated", "platform_id", "calculated_at"),
        Index("ix_eis_scores_priority_value", "priority", "eis_value"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    platform_id: Mapped[UUID] = mapped_column(
        ForeignKey("geo_platforms.id", ondelete="CASCADE"), nullable=False
    )
    query_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("frozen_prompt_instances.id", ondelete="SET NULL")
    )
    ai_engine: Mapped[str] = mapped_column(String(60), nullable=False)
    model_type: Mapped[str] = mapped_column(String(30), nullable=False)
    eis_value: Mapped[float | None] = mapped_column(Float)
    priority: Mapped[str | None] = mapped_column(String(8))
    components: Mapped[dict] = mapped_column(JSON, nullable=False)
    signal_probabilities: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False)
    explanation: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(30), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(30), nullable=False)
    weight_set_version: Mapped[str] = mapped_column(String(30), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
