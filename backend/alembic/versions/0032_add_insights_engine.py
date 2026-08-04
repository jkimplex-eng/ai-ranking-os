"""Add deterministic Insights Engine history.

Revision ID: 0032
Revises: 0031
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "insight_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("engine_version", sa.String(length=50), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("source_record_count", sa.Integer(), nullable=False),
        sa.Column("insight_count", sa.Integer(), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_insight_runs_calculated_id", "insight_runs", ["calculated_at", "id"])
    op.create_table(
        "insights",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("insight_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("insight_type", sa.String(length=30), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.String(length=300)),
        sa.Column("metric", sa.String(length=50)),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("previous_value", sa.Float()),
        sa.Column("current_value", sa.Float()),
        sa.Column("absolute_change", sa.Float()),
        sa.Column("percentage_change", sa.Float()),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.Text()),
    )
    op.create_index("ix_insights_entity_metric", "insights", ["entity_id", "metric"])
    op.create_index("ix_insights_run_type", "insights", ["run_id", "insight_type"])


def downgrade() -> None:
    op.drop_index("ix_insights_run_type", table_name="insights")
    op.drop_index("ix_insights_entity_metric", table_name="insights")
    op.drop_table("insights")
    op.drop_index("ix_insight_runs_calculated_id", table_name="insight_runs")
    op.drop_table("insight_runs")
