"""add cache

Revision ID: 0038
Revises: 0037
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.create_table(
        "cache_warm_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("namespace", sa.String(100), nullable=False),
        sa.Column("items_warmed", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("cache_warm_runs")
