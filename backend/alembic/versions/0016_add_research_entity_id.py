"""Add tracked entity ID to Research.

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "researches",
        sa.Column("entity_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_researches_entity_id",
        "researches",
        ["entity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_researches_entity_id", table_name="researches")
    op.drop_column("researches", "entity_id")
