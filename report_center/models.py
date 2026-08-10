from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ReportCatalogEntry(Base):
    __tablename__ = "report_catalog_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    research_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class ReportVersion(Base):
    __tablename__ = "report_versions"
    __table_args__ = (
        UniqueConstraint("research_id", "version", name="uq_report_version_number"),
        UniqueConstraint("research_id", "checksum", name="uq_report_version_checksum"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    research_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    catalog_entry_id: Mapped[int] = mapped_column(
        ForeignKey("report_catalog_entries.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
