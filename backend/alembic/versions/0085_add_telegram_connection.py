"""add encrypted Telegram MTProto connection

Revision ID: 0085
Revises: 0084
"""

import sqlalchemy as sa
from alembic import op

revision = "0085"
down_revision = "0084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("api_id", sa.Integer(), nullable=False),
        sa.Column("encrypted_api_hash", sa.Text(), nullable=False),
        sa.Column("encrypted_phone", sa.Text(), nullable=False),
        sa.Column("encrypted_session", sa.Text()),
        sa.Column("encrypted_code_hash", sa.Text()),
        sa.Column("encrypted_proxy", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING_CODE"),
        sa.Column("phone_hint", sa.String(30), nullable=False),
        sa.Column("last_error", sa.Text()),
        sa.Column("last_connected_at", sa.DateTime(timezone=True)),
        sa.Column("next_search_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("user_id", name="uq_telegram_connections_user"),
    )
    op.create_index("ix_telegram_connections_user_id", "telegram_connections", ["user_id"])
    op.create_index(
        "ix_telegram_connections_due", "telegram_connections", ["status", "next_search_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_telegram_connections_due", table_name="telegram_connections")
    op.drop_index("ix_telegram_connections_user_id", table_name="telegram_connections")
    op.drop_table("telegram_connections")
