from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class FrozenPromptSet(Base):
    __tablename__ = "frozen_prompt_sets"
    __table_args__ = (
        Index("uq_frozen_prompt_sets_code_version", "code", "version", unique=True),
        Index("ix_frozen_prompt_sets_active", "code", "active"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    region: Mapped[str] = mapped_column(String(16), nullable=False)
    templates: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    frozen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sql_text("CURRENT_TIMESTAMP"), nullable=False
    )
    instances: Mapped[list["FrozenPromptInstance"]] = relationship(
        back_populates="prompt_set",
        cascade="all, delete-orphan",
        order_by="FrozenPromptInstance.position",
    )


class FrozenPromptInstance(Base):
    __tablename__ = "frozen_prompt_instances"
    __table_args__ = (
        Index("uq_frozen_prompt_instance_key", "prompt_set_id", "stable_key", unique=True),
        Index("ix_frozen_prompt_instances_type", "prompt_set_id", "query_type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    prompt_set_id: Mapped[UUID] = mapped_column(
        ForeignKey("frozen_prompt_sets.id", ondelete="CASCADE"), nullable=False
    )
    stable_key: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    query_type: Mapped[str] = mapped_column(String(40), nullable=False)
    variables: Mapped[dict] = mapped_column(JSON, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sql_text("CURRENT_TIMESTAMP"), nullable=False
    )
    prompt_set: Mapped[FrozenPromptSet] = relationship(back_populates="instances")
