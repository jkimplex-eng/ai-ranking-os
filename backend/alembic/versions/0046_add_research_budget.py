"""add per research routing budget

Revision ID: 0046
Revises: 0045
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0046"
down_revision: str | None = "0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "router_policies",
        sa.Column("per_research_budget_usd", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("router_policies", "per_research_budget_usd")
