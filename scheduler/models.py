from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class ScheduleType(StrEnum):
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    CRON = "CRON"


class ScheduleExecutionStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


schedule_type = Enum(
    ScheduleType, name="schedule_type", native_enum=False, validate_strings=True, length=20
)
execution_status_type = Enum(
    ScheduleExecutionStatus,
    name="schedule_execution_status",
    native_enum=False,
    validate_strings=True,
    length=20,
)


class Schedule(Base):
    __tablename__ = "schedules"
    __table_args__ = (
        Index("ix_schedules_enabled_next_run", "is_enabled", "next_run_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    research_id: Mapped[int] = mapped_column(Integer, nullable=False)
    schedule_type: Mapped[ScheduleType] = mapped_column(schedule_type, nullable=False)
    cron_expression: Mapped[str | None] = mapped_column(String(100))
    models: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    query: Mapped[str | None] = mapped_column(Text)
    retry_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    executions: Mapped[list["ScheduleExecution"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )


class ScheduleExecution(Base):
    __tablename__ = "schedule_executions"
    __table_args__ = (
        Index("ix_schedule_executions_schedule_started", "schedule_id", "started_at"),
        Index(
            "uq_schedule_executions_one_running",
            "schedule_id",
            unique=True,
            postgresql_where=text("status = 'RUNNING'"),
            sqlite_where=text("status = 'RUNNING'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False
    )
    research_id: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[ScheduleExecutionStatus] = mapped_column(
        execution_status_type, nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    schedule: Mapped[Schedule] = relationship(back_populates="executions")
    history: Mapped[list["ScheduleHistory"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )


class ScheduleHistory(Base):
    __tablename__ = "schedule_history"
    __table_args__ = (
        Index("ix_schedule_history_execution_attempt", "execution_id", "attempt"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_executions.id", ondelete="CASCADE"), nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ScheduleExecutionStatus] = mapped_column(
        execution_status_type, nullable=False
    )
    research_id: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    retry_delay_seconds: Mapped[float] = mapped_column(default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    execution: Mapped[ScheduleExecution] = relationship(back_populates="history")

