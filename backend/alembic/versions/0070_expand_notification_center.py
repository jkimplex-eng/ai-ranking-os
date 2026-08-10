"""expand notification center

Revision ID: 0070
Revises: 0069
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0070"
down_revision: str | None = "0069"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_notifications",
        sa.Column("category", sa.String(30), nullable=False, server_default="SYSTEM"),
    )
    op.add_column(
        "product_notifications",
        sa.Column("priority", sa.String(20), nullable=False, server_default="NORMAL"),
    )
    op.add_column(
        "product_notifications", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "product_notifications",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_product_notifications_archived_at", "product_notifications", ["archived_at"]
    )
    op.create_index(
        "ix_product_notifications_user_inbox",
        "product_notifications",
        ["user_id", "archived_at", "is_read", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_product_notifications_user_inbox", table_name="product_notifications")
    op.drop_index("ix_product_notifications_archived_at", table_name="product_notifications")
    op.drop_column("product_notifications", "archived_at")
    op.drop_column("product_notifications", "read_at")
    op.drop_column("product_notifications", "priority")
    op.drop_column("product_notifications", "category")
