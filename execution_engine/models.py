from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ExecutionState(StrEnum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    WAITING_REVIEW = "WAITING_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


execution_state_type = Enum(
    ExecutionState,
    name="execution_state",
    native_enum=False,
    validate_strings=True,
    length=20,
)


class Execution(Base):
    __tablename__ = "executions"
    __table_args__ = (
        Index("ix_executions_state_finished_at", "state", "finished_at"),
        Index(
            "uq_executions_active_task",
            "task_id",
            unique=True,
            postgresql_where=text("state IN ('PENDING', 'ASSIGNED', 'RUNNING', 'WAITING_REVIEW')"),
            sqlite_where=text("state IN ('PENDING', 'ASSIGNED', 'RUNNING', 'WAITING_REVIEW')"),
        ),
        Index(
            "uq_executions_active_agent",
            "agent_id",
            unique=True,
            postgresql_where=text(
                "state IN ('ASSIGNED', 'RUNNING', 'WAITING_REVIEW') AND agent_id IS NOT NULL"
            ),
            sqlite_where=text(
                "state IN ('ASSIGNED', 'RUNNING', 'WAITING_REVIEW') AND agent_id IS NOT NULL"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), index=True)
    state: Mapped[ExecutionState] = mapped_column(
        execution_state_type,
        default=ExecutionState.PENDING,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
