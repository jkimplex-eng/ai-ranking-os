from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ProviderRecord(Base):
    __tablename__ = "provider_registry"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    pricing: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    context_window: Mapped[int] = mapped_column(Integer, nullable=False)
    vision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    embeddings: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reasoning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tools: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    json_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    streaming: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    availability: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    free_tier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, index=True)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
