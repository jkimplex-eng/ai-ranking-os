"""add task routing policies

Revision ID: 0045
Revises: 0044
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0045"
down_revision: str | None = "0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("router_policies", sa.Column("task_type", sa.String(100), nullable=True))
    op.add_column(
        "router_policies",
        sa.Column("strategy", sa.String(30), nullable=False, server_default="BALANCED"),
    )
    op.create_index("ix_router_policies_task_type", "router_policies", ["task_type"])


def downgrade() -> None:
    op.drop_index("ix_router_policies_task_type", table_name="router_policies")
    op.drop_column("router_policies", "strategy")
    op.drop_column("router_policies", "task_type")
