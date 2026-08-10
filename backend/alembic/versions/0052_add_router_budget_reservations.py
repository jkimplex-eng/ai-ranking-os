"""add atomic router budget reservations

Revision ID: 0052
Revises: 0051
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0052"
down_revision: str | None = "0051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE router_models SET provider = 'ollama' WHERE provider = 'local'")
    op.create_table(
        "router_budget_reservations",
        sa.Column("id", sa.String(200), primary_key=True),
        sa.Column("correlation_id", sa.String(200), nullable=False, unique=True),
        sa.Column("policy_id", sa.String(100), nullable=False),
        sa.Column("amount_usd", sa.Float(), nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_budget_reservation_correlation",
        "router_budget_reservations",
        ["correlation_id"],
    )
    op.create_index("ix_budget_reservation_policy", "router_budget_reservations", ["policy_id"])
    op.create_index("ix_budget_reservation_state", "router_budget_reservations", ["state"])
    op.create_index("ix_budget_reservation_created", "router_budget_reservations", ["created_at"])
    op.create_index("ix_budget_reservation_expires", "router_budget_reservations", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_budget_reservation_expires", table_name="router_budget_reservations")
    op.drop_index("ix_budget_reservation_created", table_name="router_budget_reservations")
    op.drop_index("ix_budget_reservation_state", table_name="router_budget_reservations")
    op.drop_index("ix_budget_reservation_policy", table_name="router_budget_reservations")
    op.drop_index("ix_budget_reservation_correlation", table_name="router_budget_reservations")
    op.drop_table("router_budget_reservations")
    op.execute("UPDATE router_models SET provider = 'local' WHERE provider = 'ollama'")
