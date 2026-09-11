from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
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


class WordstatConnection(Base):
    __tablename__ = "yandex_wordstat_connections"
    __table_args__ = (UniqueConstraint("organization_id", name="uq_wordstat_connection_org"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    folder_id: Mapped[str] = mapped_column(String(200), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(20), nullable=False, default="API_KEY")
    credential_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CONNECTED")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class WordstatDemandSnapshot(Base):
    __tablename__ = "yandex_wordstat_snapshots"
    __table_args__ = (
        Index("ix_wordstat_snapshot_org_brand_created", "organization_id", "brand", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    brand: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(500), nullable=False)
    region_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    device: Mapped[str] = mapped_column(String(20), nullable=False, default="all")
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    queries: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    raw_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    limitations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    algorithm_version: Mapped[str] = mapped_column(String(30), nullable=False, default="1.0")
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
