"""Add quality baselines, snapshots, and regression events.

Revision ID: 0023
Revises: 0022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "baselines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("research_id", sa.Integer(), nullable=False),
        sa.Column("update_policy", sa.String(length=30), nullable=False),
        sa.Column("thresholds", sa.JSON(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
    )
    op.create_table(
        "baseline_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "baseline_id", sa.Integer(),
            sa.ForeignKey("baselines.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("research_id", sa.Integer(), nullable=False),
        sa.Column("visibility", sa.Float(), nullable=False),
        sa.Column("mention", sa.Float(), nullable=False),
        sa.Column("recommendation", sa.Float(), nullable=False),
        sa.Column("citation", sa.Float(), nullable=False),
        sa.Column("coverage", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=50), nullable=False),
        sa.Column("algorithm_version", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
    )
    op.create_index(
        "ix_baseline_snapshots_baseline_created",
        "baseline_snapshots", ["baseline_id", "created_at"],
    )
    op.create_table(
        "regression_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "baseline_id", sa.Integer(),
            sa.ForeignKey("baselines.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "baseline_snapshot_id", sa.Integer(),
            sa.ForeignKey("baseline_snapshots.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("current_research_id", sa.Integer(), nullable=False),
        sa.Column("metric", sa.String(length=30), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False),
        sa.Column("delta", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("algorithm_version", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
    )
    op.create_index(
        "ix_regression_events_baseline_created",
        "regression_events", ["baseline_id", "created_at"],
    )
    op.create_index(
        "ix_regression_events_snapshot_id",
        "regression_events", ["baseline_snapshot_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_regression_events_snapshot_id", table_name="regression_events")
    op.drop_index("ix_regression_events_baseline_created", table_name="regression_events")
    op.drop_table("regression_events")
    op.drop_index(
        "ix_baseline_snapshots_baseline_created", table_name="baseline_snapshots"
    )
    op.drop_table("baseline_snapshots")
    op.drop_table("baselines")

