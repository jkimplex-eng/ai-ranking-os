"""add research change detection results

Revision ID: 0065
Revises: 0064
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0065"
down_revision: str | None = "0064"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("research_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("previous_research_id", sa.Integer(), nullable=True),
        sa.Column("metric_deltas", sa.JSON(), nullable=False),
        sa.Column("new_recommendations", sa.JSON(), nullable=False),
        sa.Column("removed_recommendations", sa.JSON(), nullable=False),
        sa.Column("new_sources", sa.JSON(), nullable=False),
        sa.Column("removed_sources", sa.JSON(), nullable=False),
        sa.Column("graph_changes", sa.JSON(), nullable=False),
        sa.Column("algorithm_version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_research_changes_research_id", "research_changes", ["research_id"])


def downgrade() -> None:
    op.drop_index("ix_research_changes_research_id", table_name="research_changes")
    op.drop_table("research_changes")
