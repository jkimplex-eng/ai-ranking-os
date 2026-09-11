"""add provider project credential

Revision ID: 0074
Revises: 0073
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0074"
down_revision: str | None = "0073"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("provider_connections", sa.Column("project_ciphertext", sa.Text()))


def downgrade() -> None:
    op.drop_column("provider_connections", "project_ciphertext")
