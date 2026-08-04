"""Add versioned Alert Engine rules and event history.

Revision ID: 0021
Revises: 0020
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("alert_type", sa.String(length=60), nullable=False),
        sa.Column("threshold", sa.Float()),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "uq_alert_rules_code_version",
        "alert_rules",
        ["code", "version"],
        unique=True,
    )
    op.create_index(
        "ix_alert_rules_active_version",
        "alert_rules",
        ["is_active", "version"],
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("alert_rules.id"), nullable=False),
        sa.Column("alert_type", sa.String(length=60), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("previous_value", sa.Float()),
        sa.Column("current_value", sa.Float()),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_alerts_entity_detected", "alerts", ["entity_id", "detected_at"])
    op.create_index("ix_alerts_rule_id", "alerts", ["rule_id"])
    op.create_table(
        "alert_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "alert_id",
            sa.Integer(),
            sa.ForeignKey("alerts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_alert_events_alert_created", "alert_events", ["alert_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_alert_events_alert_created", table_name="alert_events")
    op.drop_table("alert_events")
    op.drop_index("ix_alerts_rule_id", table_name="alerts")
    op.drop_index("ix_alerts_entity_detected", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_alert_rules_active_version", table_name="alert_rules")
    op.drop_index("uq_alert_rules_code_version", table_name="alert_rules")
    op.drop_table("alert_rules")

