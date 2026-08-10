"""add product analytics

Revision ID: 0069
Revises: 0068
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0069"
down_revision: str | None = "0068"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_analytics_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("event_name", sa.String(100), nullable=False),
        sa.Column("event_category", sa.String(30), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_product_analytics_event_time_category",
        "product_analytics_events",
        ["created_at", "event_category"],
    )
    op.create_index(
        "ix_product_analytics_event_org_time",
        "product_analytics_events",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_product_analytics_event_user_time",
        "product_analytics_events",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_product_analytics_event_name_time",
        "product_analytics_events",
        ["event_name", "created_at"],
    )
    op.create_table(
        "product_analytics_sessions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("device", sa.String(50), nullable=False),
        sa.Column("browser", sa.String(80), nullable=False),
        sa.Column("os", sa.String(80), nullable=False),
    )
    op.create_index(
        "ix_product_analytics_sessions_user_id", "product_analytics_sessions", ["user_id"]
    )
    op.create_index(
        "ix_product_analytics_sessions_organization_id",
        "product_analytics_sessions",
        ["organization_id"],
    )
    op.create_table(
        "product_analytics_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("filters_hash", sa.String(64), nullable=False),
        sa.Column("range_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("range_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_product_analytics_report_period",
        "product_analytics_reports",
        ["period", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_product_analytics_report_period", table_name="product_analytics_reports")
    op.drop_table("product_analytics_reports")
    op.drop_index(
        "ix_product_analytics_sessions_organization_id",
        table_name="product_analytics_sessions",
    )
    op.drop_index(
        "ix_product_analytics_sessions_user_id", table_name="product_analytics_sessions"
    )
    op.drop_table("product_analytics_sessions")
    op.drop_index(
        "ix_product_analytics_event_name_time", table_name="product_analytics_events"
    )
    op.drop_index(
        "ix_product_analytics_event_user_time", table_name="product_analytics_events"
    )
    op.drop_index(
        "ix_product_analytics_event_org_time", table_name="product_analytics_events"
    )
    op.drop_index(
        "ix_product_analytics_event_time_category", table_name="product_analytics_events"
    )
    op.drop_table("product_analytics_events")
