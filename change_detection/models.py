from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ResearchChange(Base):
    __tablename__ = "research_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    research_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    previous_research_id: Mapped[int | None] = mapped_column(Integer)
    metric_deltas: Mapped[dict] = mapped_column(JSON, nullable=False)
    new_recommendations: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    removed_recommendations: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    new_sources: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    removed_sources: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    graph_changes: Mapped[dict] = mapped_column(JSON, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
