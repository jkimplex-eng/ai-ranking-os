"""scope publication platforms to the organization that produced them

Revision ID: 0091_scope_geo_platforms
Revises: 0090_tbank_payments
"""

import sqlalchemy as sa
from alembic import op

revision = "0091_scope_geo_platforms"
down_revision = "0090_tbank_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("geo_platforms", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_geo_platforms_organization", "geo_platforms", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE",
    )
    # Backfill only rows whose stored research points to an existing organization.
    # Unattributed legacy/manual rows remain quarantined rather than being
    # assigned to a guessed tenant.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            UPDATE geo_platforms AS p
            SET organization_id = (r.metadata_payload ->> 'organization_id')::integer
            FROM researches AS r
            WHERE p.source = 'YANDEX_SEARCH_GENERATIVE'
              AND p.source_reference = 'research:' || r.id::text
              AND (r.metadata_payload ->> 'organization_id') ~ '^[0-9]+$'
              AND EXISTS (
                  SELECT 1 FROM organizations AS o
                  WHERE o.id = (r.metadata_payload ->> 'organization_id')::integer
              )
        """)
    op.drop_index("uq_geo_platforms_domain", table_name="geo_platforms")
    op.create_index(
        "uq_geo_platforms_organization_domain", "geo_platforms",
        ["organization_id", "domain"], unique=True,
    )
    op.create_index("ix_geo_platforms_organization_id", "geo_platforms", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_geo_platforms_organization_id", table_name="geo_platforms")
    op.drop_index("uq_geo_platforms_organization_domain", table_name="geo_platforms")
    op.create_index("uq_geo_platforms_domain", "geo_platforms", ["domain"], unique=True)
    op.drop_constraint("fk_geo_platforms_organization", "geo_platforms", type_="foreignkey")
    op.drop_column("geo_platforms", "organization_id")
