from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class GeoPlatform(Base):
    __tablename__ = "geo_platforms"
    __table_args__ = (
        Index("uq_geo_platforms_domain", "domain", unique=True),
        Index("ix_geo_platforms_category_language", "category", "language"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    platform_type: Mapped[str] = mapped_column(String(60), nullable=False, default="PUBLICATION")
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="UNIVERSAL")
    country: Mapped[str] = mapped_column(String(8), nullable=False, default="GLOBAL")
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="ALL")
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="MANUAL")
    source_reference: Mapped[str | None] = mapped_column(Text)
    ai_engines: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    domain_trust: Mapped[float | None] = mapped_column(Float)
    topical_authority_score: Mapped[float | None] = mapped_column(Float)
    ai_citation_history: Mapped[int | None] = mapped_column(Integer)
    allows_ai_crawlers: Mapped[bool | None] = mapped_column(Boolean)
    in_knowledge_graph: Mapped[bool | None] = mapped_column(Boolean)
    branded_mentions_90d: Mapped[int | None] = mapped_column(Integer)
    youtube_mentions: Mapped[int | None] = mapped_column(Integer)
    branded_anchors: Mapped[int | None] = mapped_column(Integer)
    branded_search_volume: Mapped[float | None] = mapped_column(Float)
    schema_markup_types: Mapped[list[str] | None] = mapped_column(JSON)
    has_direct_answer: Mapped[bool | None] = mapped_column(Boolean)
    content_freshness_days: Mapped[int | None] = mapped_column(Integer)
    has_structured_lists: Mapped[bool | None] = mapped_column(Boolean)
    self_contained_paragraph_score: Mapped[float | None] = mapped_column(Float)
    cost_per_placement: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class GeoPlatformImport(Base):
    __tablename__ = "geo_platform_imports"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    rows_total: Mapped[int] = mapped_column(Integer, nullable=False)
    rows_imported: Mapped[int] = mapped_column(Integer, nullable=False)
    rows_failed: Mapped[int] = mapped_column(Integer, nullable=False)
    errors: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
