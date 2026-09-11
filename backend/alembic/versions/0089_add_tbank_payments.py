"""add T-Bank payments

Revision ID: 0089
Revises: 0088
"""

import sqlalchemy as sa
from alembic import op

revision = "0089"
down_revision = "0088"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tbank_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_code", sa.String(40), nullable=False),
        sa.Column("order_id", sa.String(50), nullable=False, unique=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="NEW"),
        sa.Column("payment_id", sa.String(100), unique=True),
        sa.Column("payment_url", sa.Text()),
        sa.Column("raw_notification", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_tbank_payments_user_id", "tbank_payments", ["user_id"])
    op.create_index("ix_tbank_payments_order_id", "tbank_payments", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_tbank_payments_order_id", table_name="tbank_payments")
    op.drop_index("ix_tbank_payments_user_id", table_name="tbank_payments")
    op.drop_table("tbank_payments")
