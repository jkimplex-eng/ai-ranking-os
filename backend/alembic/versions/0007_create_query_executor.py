"""Create Query Executor history and metrics.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "query_execution_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("execution_id", sa.String(length=200), nullable=False),
        sa.Column("plan_id", sa.String(length=200), nullable=False),
        sa.Column("request_id", sa.String(length=200), nullable=True),
        sa.Column("mode", sa.String(length=30), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("plan_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_id"),
    )
    op.create_index(
        "ix_query_execution_history_execution_id",
        "query_execution_history",
        ["execution_id"],
        unique=True,
    )
    op.create_index(
        "ix_query_execution_history_mode",
        "query_execution_history",
        ["mode"],
    )
    op.create_index(
        "ix_query_execution_history_plan_id",
        "query_execution_history",
        ["plan_id"],
    )
    op.create_index(
        "ix_query_execution_history_request_id",
        "query_execution_history",
        ["request_id"],
    )
    op.create_index(
        "ix_query_execution_history_state",
        "query_execution_history",
        ["state"],
    )
    op.create_table(
        "query_execution_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("execution_row_id", sa.Integer(), nullable=False),
        sa.Column("execution_id", sa.String(length=200), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_row_id"],
            ["query_execution_history.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_query_execution_metrics_execution_id",
        "query_execution_metrics",
        ["execution_id"],
    )
    op.create_index(
        "ix_query_execution_metrics_metric_name",
        "query_execution_metrics",
        ["metric_name"],
    )
    op.create_table(
        "query_provider_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("execution_row_id", sa.Integer(), nullable=False),
        sa.Column("execution_id", sa.String(length=200), nullable=False),
        sa.Column("step_id", sa.String(length=200), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("failure", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["execution_row_id"],
            ["query_execution_history.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_query_provider_metrics_execution_id",
        "query_provider_metrics",
        ["execution_id"],
    )
    op.create_index(
        "ix_query_provider_metrics_provider",
        "query_provider_metrics",
        ["provider"],
    )
    op.create_index(
        "ix_query_provider_metrics_state",
        "query_provider_metrics",
        ["state"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_query_provider_metrics_state",
        table_name="query_provider_metrics",
    )
    op.drop_index(
        "ix_query_provider_metrics_provider",
        table_name="query_provider_metrics",
    )
    op.drop_index(
        "ix_query_provider_metrics_execution_id",
        table_name="query_provider_metrics",
    )
    op.drop_table("query_provider_metrics")
    op.drop_index(
        "ix_query_execution_metrics_metric_name",
        table_name="query_execution_metrics",
    )
    op.drop_index(
        "ix_query_execution_metrics_execution_id",
        table_name="query_execution_metrics",
    )
    op.drop_table("query_execution_metrics")
    op.drop_index(
        "ix_query_execution_history_state",
        table_name="query_execution_history",
    )
    op.drop_index(
        "ix_query_execution_history_request_id",
        table_name="query_execution_history",
    )
    op.drop_index(
        "ix_query_execution_history_plan_id",
        table_name="query_execution_history",
    )
    op.drop_index(
        "ix_query_execution_history_mode",
        table_name="query_execution_history",
    )
    op.drop_index(
        "ix_query_execution_history_execution_id",
        table_name="query_execution_history",
    )
    op.drop_table("query_execution_history")

