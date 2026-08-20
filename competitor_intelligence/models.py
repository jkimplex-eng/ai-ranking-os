from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class CompetitorDailySnapshot(Base):
    __tablename__ = "competitor_daily_snapshots"
    __table_args__ = (
        UniqueConstraint("competitor_id", "snapshot_date", name="uq_competitor_snapshot_day"),
        Index("ix_competitor_snapshots_competitor_date", "competitor_id", "snapshot_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("project_competitors.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    research_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    response_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mention_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recommendation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    citation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    observed_visibility_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(30), default="1.0", nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class CompetitorPublicationObservation(Base):
    __tablename__ = "competitor_publication_observations"
    __table_args__ = (
        UniqueConstraint(
            "competitor_id", "response_id", "url", name="uq_competitor_publication_response"
        ),
        Index("ix_competitor_publications_competitor_seen", "competitor_id", "last_seen_at"),
        Index("ix_competitor_publications_domain", "domain"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("project_competitors.id", ondelete="CASCADE"), nullable=False
    )
    research_id: Mapped[int] = mapped_column(
        ForeignKey("researches.id", ondelete="CASCADE"), nullable=False
    )
    response_id: Mapped[int] = mapped_column(
        ForeignKey("research_responses.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    mentioned: Mapped[bool] = mapped_column(default=False, nullable=False)
    recommended: Mapped[bool] = mapped_column(default=False, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)
    evidence_level: Mapped[str] = mapped_column(
        String(30), default="OBSERVATION", nullable=False
    )
