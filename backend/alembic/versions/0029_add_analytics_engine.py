"""Add Analytics Engine run history.

Revision ID: 0029
Revises: 0028
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analytics_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("engine_version", sa.String(length=50), nullable=False),
        sa.Column("query_payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=False),
        sa.Column("source_record_count", sa.Integer(), nullable=False),
        sa.Column("group_count", sa.Integer(), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_analytics_runs_calculated_id", "analytics_runs", ["calculated_at", "id"])
    op.create_index(
        "ix_analytics_runs_version_calculated",
        "analytics_runs",
        ["engine_version", "calculated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_analytics_runs_version_calculated", table_name="analytics_runs")
    op.drop_index("ix_analytics_runs_calculated_id", table_name="analytics_runs")
    op.drop_table("analytics_runs")
