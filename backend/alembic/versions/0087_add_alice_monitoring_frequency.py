"""add Alice monitoring cadence

Revision ID: 0087
Revises: 0086
"""

import sqlalchemy as sa
from alembic import op

revision = "0087"
down_revision = "0086"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "alice_automation_plans",
        sa.Column(
            "monitoring_frequency",
            sa.String(20),
            nullable=False,
            server_default="DAILY",
        ),
    )


def downgrade() -> None:
    op.drop_column("alice_automation_plans", "monitoring_frequency")
