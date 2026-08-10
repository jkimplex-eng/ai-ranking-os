"""add report center metadata

Revision ID: 0061
Revises: 0060
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0061"
down_revision: str | None = "0060"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_catalog_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("research_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_report_catalog_entries_research_id",
        "report_catalog_entries",
        ["research_id"],
    )
    op.create_index(
        "ix_report_catalog_entries_project_id",
        "report_catalog_entries",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_catalog_entries_project_id", table_name="report_catalog_entries"
    )
    op.drop_index(
        "ix_report_catalog_entries_research_id", table_name="report_catalog_entries"
    )
    op.drop_table("report_catalog_entries")
