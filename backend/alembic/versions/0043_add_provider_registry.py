"""add provider registry

Revision ID: 0043
Revises: 0042
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0043"
down_revision: str | None = "0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_registry",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("pricing", sa.JSON(), nullable=False),
        sa.Column("context_window", sa.Integer(), nullable=False),
        sa.Column("vision", sa.Boolean(), nullable=False),
        sa.Column("embeddings", sa.Boolean(), nullable=False),
        sa.Column("reasoning", sa.Boolean(), nullable=False),
        sa.Column("tools", sa.Boolean(), nullable=False),
        sa.Column("json_mode", sa.Boolean(), nullable=False),
        sa.Column("streaming", sa.Boolean(), nullable=False),
        sa.Column("availability", sa.String(30), nullable=False),
        sa.Column("free_tier", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_provider_registry_availability", "provider_registry", ["availability"])
    op.create_index("ix_provider_registry_free_tier", "provider_registry", ["free_tier"])
    op.create_index("ix_provider_registry_priority", "provider_registry", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_provider_registry_priority", table_name="provider_registry")
    op.drop_index("ix_provider_registry_free_tier", table_name="provider_registry")
    op.drop_index("ix_provider_registry_availability", table_name="provider_registry")
    op.drop_table("provider_registry")
