"""add immutable report versions

Revision ID: 0062
Revises: 0061
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0062"
down_revision: str | None = "0061"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("research_id", sa.Integer(), nullable=False),
        sa.Column(
            "catalog_entry_id",
            sa.Integer(),
            sa.ForeignKey("report_catalog_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("research_id", "version", name="uq_report_version_number"),
        sa.UniqueConstraint("research_id", "checksum", name="uq_report_version_checksum"),
    )
    op.create_index("ix_report_versions_research_id", "report_versions", ["research_id"])


def downgrade() -> None:
    op.drop_index("ix_report_versions_research_id", table_name="report_versions")
    op.drop_table("report_versions")
