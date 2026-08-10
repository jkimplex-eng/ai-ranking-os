"""add provider recommendations

Revision ID: 0051
Revises: 0050
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0051"
down_revision: str | None = "0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("research_id", sa.Integer(), nullable=False),
        sa.Column("recommendation_type", sa.String(100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("recommended_provider", sa.String(100), nullable=False),
        sa.Column("expected_savings_usd", sa.Float(), nullable=False),
        sa.Column("expected_speedup_percent", sa.Float(), nullable=False),
        sa.Column("version", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name in ("research_id", "recommendation_type", "created_at"):
        op.create_index(f"ix_provider_recommendations_{name}", "provider_recommendations", [name])


def downgrade() -> None:
    op.drop_table("provider_recommendations")
