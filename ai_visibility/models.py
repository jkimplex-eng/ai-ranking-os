from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class VisibilityWeightSet(Base):
    __tablename__ = "visibility_weight_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(50), unique=True)
    weights: Mapped[dict[str, float]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class VisibilityCalculation(Base):
    __tablename__ = "visibility_calculations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(200), index=True)
    entity: Mapped[str] = mapped_column(String(300))
    visibility_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    metrics: Mapped[dict[str, float]] = mapped_column(JSON)
    weights: Mapped[dict[str, float]] = mapped_column(JSON)
    weight_version: Mapped[str] = mapped_column(String(50), index=True)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

