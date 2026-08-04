"""Add Benchmark Engine snapshots.

Revision ID: 0031
Revises: 0030
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "benchmark_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("engine_version", sa.String(length=50), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("entity_count", sa.Integer(), nullable=False),
        sa.Column("date_from", sa.DateTime(timezone=True)),
        sa.Column("date_to", sa.DateTime(timezone=True)),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_benchmark_runs_calculated_id", "benchmark_runs", ["calculated_at", "id"])
    op.create_table(
        "benchmark_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("benchmark_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_id", sa.String(length=300), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("metric_results", sa.JSON(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("overall_rank", sa.Integer(), nullable=False),
        sa.Column("overall_percentile", sa.Float(), nullable=False),
    )
    op.create_index("ix_benchmark_entries_entity", "benchmark_entries", ["entity_id"])
    op.create_index(
        "ix_benchmark_entries_run_rank", "benchmark_entries", ["run_id", "overall_rank"]
    )
    op.create_index(
        "uq_benchmark_entries_run_entity",
        "benchmark_entries",
        ["run_id", "entity_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_benchmark_entries_run_entity", table_name="benchmark_entries")
    op.drop_index("ix_benchmark_entries_run_rank", table_name="benchmark_entries")
    op.drop_index("ix_benchmark_entries_entity", table_name="benchmark_entries")
    op.drop_table("benchmark_entries")
    op.drop_index("ix_benchmark_runs_calculated_id", table_name="benchmark_runs")
    op.drop_table("benchmark_runs")
