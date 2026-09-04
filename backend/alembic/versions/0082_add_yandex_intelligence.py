"""add Yandex Intelligence snapshots

Revision ID: 0082
Revises: 0081
"""

import sqlalchemy as sa
from alembic import op

revision = "0082"
down_revision = "0081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "yandex_intelligence_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("host_id", sa.String(500), nullable=False),
        sa.Column("host_url", sa.String(500), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("evidence_status", sa.String(30), nullable=False),
        sa.Column("webmaster_evidence", sa.JSON(), nullable=False),
        sa.Column("yandex_ai_evidence", sa.JSON(), nullable=False),
        sa.Column("query_map", sa.JSON(), nullable=False),
        sa.Column("opportunities", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("algorithm_version", sa.String(30), nullable=False, server_default="1.0"),
        sa.Column("error", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_yandex_intelligence_snapshots_org",
        "yandex_intelligence_snapshots",
        ["organization_id"],
    )
    op.create_index(
        "ix_yandex_intelligence_org_host_created",
        "yandex_intelligence_snapshots",
        ["organization_id", "host_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_yandex_intelligence_org_host_created",
        table_name="yandex_intelligence_snapshots",
    )
    op.drop_index(
        "ix_yandex_intelligence_snapshots_org",
        table_name="yandex_intelligence_snapshots",
    )
    op.drop_table("yandex_intelligence_snapshots")
