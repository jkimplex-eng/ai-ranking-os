"""add closed beta administration

Revision ID: 0067
Revises: 0066
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0067"
down_revision: str | None = "0066"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "beta_user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="WAITLIST"),
        sa.Column("daily_research_limit", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("monthly_research_limit", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("max_projects", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("max_domains", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("max_organization_users", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_beta_user_profiles_user_id", "beta_user_profiles", ["user_id"])
    op.create_table(
        "beta_invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("token_prefix", sa.String(12), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=True),
        sa.Column("invited_by", sa.String(100), nullable=False),
        sa.Column("send_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_beta_invitations_email", "beta_invitations", ["email"])


def downgrade() -> None:
    op.drop_index("ix_beta_invitations_email", table_name="beta_invitations")
    op.drop_table("beta_invitations")
    op.drop_index("ix_beta_user_profiles_user_id", table_name="beta_user_profiles")
    op.drop_table("beta_user_profiles")
