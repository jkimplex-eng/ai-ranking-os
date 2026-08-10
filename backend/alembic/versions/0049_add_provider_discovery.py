"""add provider discovery history

Revision ID: 0049
Revises: 0048
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0049"
down_revision: str | None = "0048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(500), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("discovered", sa.Integer(), nullable=False),
        sa.Column("created", sa.Integer(), nullable=False),
        sa.Column("updated", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_provider_sync_runs_status", "provider_sync_runs", ["status"])
    op.create_index("ix_provider_sync_runs_created_at", "provider_sync_runs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_provider_sync_runs_created_at", table_name="provider_sync_runs")
    op.drop_index("ix_provider_sync_runs_status", table_name="provider_sync_runs")
    op.drop_table("provider_sync_runs")
