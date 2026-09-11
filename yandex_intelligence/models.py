from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class YandexIntelligenceSnapshot(Base):
    __tablename__ = "yandex_intelligence_snapshots"
    __table_args__ = (
        Index(
            "ix_yandex_intelligence_org_host_created",
            "organization_id",
            "host_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    host_id: Mapped[str] = mapped_column(String(500), nullable=False)
    host_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(30), nullable=False)
    webmaster_evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    yandex_ai_evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    query_map: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    opportunities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    limitations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    algorithm_version: Mapped[str] = mapped_column(String(30), nullable=False, default="1.0")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
