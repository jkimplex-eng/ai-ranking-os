from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class PromptStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"


class PromptDefinition(Base):
    __tablename__ = "prompt_definitions"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_prompt_definitions_code_version"),
        Index("ix_prompt_definitions_category_language", "category", "language"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50))
    language: Mapped[str] = mapped_column(String(16), default="en")
    variables: Mapped[list[str]] = mapped_column(JSON, default=list)
    template: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default=PromptStatus.DRAFT)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class ResearchTemplateDefinition(Base):
    __tablename__ = "research_template_definitions"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_research_templates_code_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    prompt_code: Mapped[str] = mapped_column(String(100))
    pipeline: Mapped[list[str]] = mapped_column(JSON, default=list)
    default_languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    default_regions: Mapped[list[str]] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
