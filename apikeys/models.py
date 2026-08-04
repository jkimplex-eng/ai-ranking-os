from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (Index("ix_api_keys_owner_active", "owner_id", "revoked_at", "expires_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    prefix: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    secret_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    rate_plan: Mapped[str] = mapped_column(String(50), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_from_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
