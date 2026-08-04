"""Add persisted trend series, snapshots, and points.

Revision ID: 0020
Revises: 0019
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trend_series",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column(
            "moving_average_window", sa.Integer(), server_default="3", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "uq_trend_series_entity_version",
        "trend_series",
        ["entity_id", "model_version"],
        unique=True,
    )
    op.create_table(
        "trend_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "series_id",
            sa.Integer(),
            sa.ForeignKey("trend_series.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column(
            "built_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_trend_snapshots_series_built",
        "trend_snapshots",
        ["series_id", "built_at"],
    )
    op.create_table(
        "trend_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.Integer(),
            sa.ForeignKey("trend_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("research_id", sa.Integer(), nullable=False),
        sa.Column("metric", sa.String(length=30), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("moving_average", sa.Float(), nullable=False),
        sa.Column("percentage_change", sa.Float()),
        sa.Column("direction", sa.String(length=10), nullable=False),
    )
    op.create_index(
        "ix_trend_points_snapshot_metric_time",
        "trend_points",
        ["snapshot_id", "metric", "observed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_trend_points_snapshot_metric_time", table_name="trend_points")
    op.drop_table("trend_points")
    op.drop_index("ix_trend_snapshots_series_built", table_name="trend_snapshots")
    op.drop_table("trend_snapshots")
    op.drop_index("uq_trend_series_entity_version", table_name="trend_series")
    op.drop_table("trend_series")

