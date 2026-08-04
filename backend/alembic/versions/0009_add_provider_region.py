"""Add provider region and success probability.

Revision ID: 0009
Revises: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "router_models",
        sa.Column(
            "region",
            sa.String(length=20),
            server_default="GLOBAL",
            nullable=False,
        ),
    )
    op.add_column(
        "router_models",
        sa.Column(
            "success_probability",
            sa.Float(),
            server_default="0.95",
            nullable=False,
        ),
    )
    op.create_index("ix_router_models_region", "router_models", ["region"])


def downgrade() -> None:
    op.drop_index("ix_router_models_region", table_name="router_models")
    op.drop_column("router_models", "success_probability")
    op.drop_column("router_models", "region")
