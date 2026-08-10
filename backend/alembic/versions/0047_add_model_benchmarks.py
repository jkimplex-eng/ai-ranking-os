"""add model benchmarks

Revision ID: 0047
Revises: 0046
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_benchmark_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("iterations", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_benchmark_runs_created_at", "model_benchmark_runs", ["created_at"])
    op.create_table(
        "model_benchmark_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("response_length", sa.Integer(), nullable=False),
        sa.Column("stability_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name in ("run_id", "provider", "model", "created_at"):
        op.create_index(f"ix_model_benchmark_results_{name}", "model_benchmark_results", [name])


def downgrade() -> None:
    op.drop_table("model_benchmark_results")
    op.drop_index("ix_model_benchmark_runs_created_at", table_name="model_benchmark_runs")
    op.drop_table("model_benchmark_runs")
