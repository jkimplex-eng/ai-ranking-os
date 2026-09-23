"""scope frozen prompt sets to their organization

Revision ID: 0092_scope_frozen_prompts
Revises: 0091_scope_geo_platforms
"""

import sqlalchemy as sa
from alembic import op

revision = "0092_scope_frozen_prompts"
down_revision = "0091_scope_geo_platforms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("frozen_prompt_sets", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_frozen_prompt_sets_organization", "frozen_prompt_sets", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE",
    )
    # Pre-existing sets have no ownership evidence. Quarantine them with NULL.
    op.drop_index("uq_frozen_prompt_sets_code_version", table_name="frozen_prompt_sets")
    op.drop_index("ix_frozen_prompt_sets_active", table_name="frozen_prompt_sets")
    op.create_index(
        "uq_frozen_prompt_sets_organization_code_version", "frozen_prompt_sets",
        ["organization_id", "code", "version"], unique=True,
    )
    op.create_index(
        "ix_frozen_prompt_sets_active", "frozen_prompt_sets",
        ["organization_id", "code", "active"],
    )
    op.create_index(
        "ix_frozen_prompt_sets_organization_id", "frozen_prompt_sets", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_frozen_prompt_sets_organization_id", table_name="frozen_prompt_sets")
    op.drop_index("ix_frozen_prompt_sets_active", table_name="frozen_prompt_sets")
    op.drop_index(
        "uq_frozen_prompt_sets_organization_code_version", table_name="frozen_prompt_sets"
    )
    op.create_index(
        "uq_frozen_prompt_sets_code_version", "frozen_prompt_sets", ["code", "version"],
        unique=True,
    )
    op.create_index(
        "ix_frozen_prompt_sets_active", "frozen_prompt_sets", ["code", "active"]
    )
    op.drop_constraint(
        "fk_frozen_prompt_sets_organization", "frozen_prompt_sets", type_="foreignkey"
    )
    op.drop_column("frozen_prompt_sets", "organization_id")
