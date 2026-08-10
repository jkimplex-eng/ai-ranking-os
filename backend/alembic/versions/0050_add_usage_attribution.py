"""add usage attribution

Revision ID: 0050
Revises: 0049
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0050"
down_revision: str | None = "0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("provider_usage", sa.Column("research_id", sa.Integer(), nullable=True))
    op.add_column("provider_usage", sa.Column("user_id", sa.String(200), nullable=True))
    op.create_index("ix_provider_usage_research_id", "provider_usage", ["research_id"])
    op.create_index("ix_provider_usage_user_id", "provider_usage", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_provider_usage_user_id", table_name="provider_usage")
    op.drop_index("ix_provider_usage_research_id", table_name="provider_usage")
    op.drop_column("provider_usage", "user_id")
    op.drop_column("provider_usage", "research_id")
