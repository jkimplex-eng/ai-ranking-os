"""add secure report sharing

Revision ID: 0063
Revises: 0062
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0063"
down_revision: str | None = "0062"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_share_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("research_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("token_prefix", sa.String(12), nullable=False),
        sa.Column("access_mode", sa.String(20), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_report_share_links_research_id", "report_share_links", ["research_id"])
    op.create_index(
        "ix_report_share_research_active",
        "report_share_links",
        ["research_id", "active"],
    )
    op.create_table(
        "report_share_views",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "share_id",
            sa.Integer(),
            sa.ForeignKey("report_share_links.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column(
            "viewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_report_share_views_share_id", "report_share_views", ["share_id"])


def downgrade() -> None:
    op.drop_index("ix_report_share_views_share_id", table_name="report_share_views")
    op.drop_table("report_share_views")
    op.drop_index("ix_report_share_research_active", table_name="report_share_links")
    op.drop_index("ix_report_share_links_research_id", table_name="report_share_links")
    op.drop_table("report_share_links")
