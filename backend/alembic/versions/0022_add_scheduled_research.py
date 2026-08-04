"""Add recurring schedules and execution history.

Revision ID: 0022
Revises: 0021
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("research_id", sa.Integer(), nullable=False),
        sa.Column("schedule_type", sa.String(length=20), nullable=False),
        sa.Column("cron_expression", sa.String(length=100)),
        sa.Column("models", sa.JSON(), nullable=False),
        sa.Column("query", sa.Text()),
        sa.Column("retry_policy", sa.JSON(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
    )
    op.create_index(
        "ix_schedules_enabled_next_run", "schedules", ["is_enabled", "next_run_at"]
    )
    op.create_table(
        "schedule_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "schedule_id", sa.Integer(),
            sa.ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("research_id", sa.Integer()),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_schedule_executions_schedule_started",
        "schedule_executions", ["schedule_id", "started_at"],
    )
    op.create_index(
        "uq_schedule_executions_one_running",
        "schedule_executions", ["schedule_id"], unique=True,
        postgresql_where=sa.text("status = 'RUNNING'"),
    )
    op.create_table(
        "schedule_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "execution_id", sa.Integer(),
            sa.ForeignKey("schedule_executions.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("research_id", sa.Integer()),
        sa.Column("error", sa.Text()),
        sa.Column("retry_delay_seconds", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_schedule_history_execution_attempt",
        "schedule_history", ["execution_id", "attempt"],
    )


def downgrade() -> None:
    op.drop_index("ix_schedule_history_execution_attempt", table_name="schedule_history")
    op.drop_table("schedule_history")
    op.drop_index("uq_schedule_executions_one_running", table_name="schedule_executions")
    op.drop_index(
        "ix_schedule_executions_schedule_started", table_name="schedule_executions"
    )
    op.drop_table("schedule_executions")
    op.drop_index("ix_schedules_enabled_next_run", table_name="schedules")
    op.drop_table("schedules")

