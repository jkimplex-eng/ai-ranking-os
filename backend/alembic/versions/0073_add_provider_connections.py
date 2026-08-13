"""add organization provider connections

Revision ID: 0073
Revises: 0072
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0073"
down_revision: str | None = "0072"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("credential_name", sa.String(100), nullable=False),
        sa.Column("secret_ciphertext", sa.Text(), nullable=False),
        sa.Column("secret_suffix", sa.String(8), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("free_only", sa.Boolean(), nullable=False),
        sa.Column("paid_fallback", sa.Boolean(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(500)),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id", "provider", name="uq_provider_connection_org_provider"
        ),
    )
    op.create_index(
        "ix_provider_connections_organization_id",
        "provider_connections",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_connections_organization_id", table_name="provider_connections"
    )
    op.drop_table("provider_connections")
