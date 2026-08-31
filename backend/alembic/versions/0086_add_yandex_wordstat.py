"""add Yandex Wordstat demand integration

Revision ID: 0086
Revises: 0085
"""

import sqlalchemy as sa
from alembic import op

revision = "0086"
down_revision = "0085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "yandex_wordstat_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("folder_id", sa.String(200), nullable=False),
        sa.Column("auth_type", sa.String(20), nullable=False, server_default="API_KEY"),
        sa.Column("credential_ciphertext", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="CONNECTED"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(500)),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("organization_id", name="uq_wordstat_connection_org"),
    )
    op.create_index(
        "ix_yandex_wordstat_connections_organization_id",
        "yandex_wordstat_connections",
        ["organization_id"],
    )
    op.create_table(
        "yandex_wordstat_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("brand", sa.String(300), nullable=False),
        sa.Column("category", sa.String(500), nullable=False),
        sa.Column("region_ids", sa.JSON(), nullable=False),
        sa.Column("device", sa.String(20), nullable=False, server_default="all"),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("queries", sa.JSON(), nullable=False),
        sa.Column("raw_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("algorithm_version", sa.String(30), nullable=False, server_default="1.0"),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_yandex_wordstat_snapshots_organization_id",
        "yandex_wordstat_snapshots",
        ["organization_id"],
    )
    op.create_index(
        "ix_wordstat_snapshot_org_brand_created",
        "yandex_wordstat_snapshots",
        ["organization_id", "brand", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_wordstat_snapshot_org_brand_created", table_name="yandex_wordstat_snapshots")
    op.drop_index(
        "ix_yandex_wordstat_snapshots_organization_id", table_name="yandex_wordstat_snapshots"
    )
    op.drop_table("yandex_wordstat_snapshots")
    op.drop_index(
        "ix_yandex_wordstat_connections_organization_id", table_name="yandex_wordstat_connections"
    )
    op.drop_table("yandex_wordstat_connections")
