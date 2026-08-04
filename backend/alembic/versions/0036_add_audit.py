"""add audit

Revision ID: 0036
Revises: 0035
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.String(100), nullable=False),
        sa.Column("actor_type", sa.String(30), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(100)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("old_state", sa.JSON()),
        sa.Column("new_state", sa.JSON()),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_time_action", "audit_events", ["created_at", "action"])
    op.create_index("ix_audit_correlation", "audit_events", ["correlation_id"])


def downgrade():
    op.drop_index("ix_audit_correlation", table_name="audit_events")
    op.drop_index("ix_audit_time_action", table_name="audit_events")
    op.drop_table("audit_events")
