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
    evidence_level: Mapped[str] = mapped_column(String(30), default="OBSERVATION", nullable=False)


class CompetitorSocialSource(Base):
    __tablename__ = "competitor_social_sources"
    __table_args__ = (
        UniqueConstraint(
            "competitor_id", "platform", "external_id", name="uq_competitor_social_source"
        ),
        Index("ix_competitor_social_sources_due", "active", "next_scan_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("project_competitors.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    profile_url: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str] = mapped_column(String(300), nullable=False)
    encrypted_token: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class CompetitorSocialPost(Base):
    __tablename__ = "competitor_social_posts"
    __table_args__ = (
        UniqueConstraint("source_id", "external_post_id", name="uq_competitor_social_post"),
        Index("ix_competitor_social_posts_source_published", "source_id", "published_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("competitor_social_sources.id", ondelete="CASCADE"), nullable=False
    )
    external_post_id: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    views: Mapped[int | None] = mapped_column(Integer)
    likes: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[int | None] = mapped_column(Integer)
    shares: Mapped[int | None] = mapped_column(Integer)
    engagement_rate: Mapped[float | None] = mapped_column(Float)
    significance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    raw_metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
