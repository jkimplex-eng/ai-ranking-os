"""add rbac

Revision ID: 0034
Revises: 0033
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rbac_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )
    op.create_table(
        "rbac_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("scope", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.UniqueConstraint("resource", "action", "scope", name="uq_rbac_permission"),
    )
    op.create_table(
        "rbac_role_permissions",
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey("rbac_roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "permission_id",
            sa.Integer(),
            sa.ForeignKey("rbac_permissions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "rbac_role_inheritance",
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey("rbac_roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "parent_role_id",
            sa.Integer(),
            sa.ForeignKey("rbac_roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "rbac_user_roles",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey("rbac_roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "assigned_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )
    op.create_index("ix_rbac_user_roles_user", "rbac_user_roles", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_rbac_user_roles_user", table_name="rbac_user_roles")
    op.drop_table("rbac_user_roles")
    op.drop_table("rbac_role_inheritance")
    op.drop_table("rbac_role_permissions")
    op.drop_table("rbac_permissions")
    op.drop_table("rbac_roles")
