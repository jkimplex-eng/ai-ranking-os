"""add workspace projects and research ownership

Revision ID: 0055
Revises: 0054
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0055"
down_revision: str | None = "0054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("user_workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("favorite", sa.Boolean(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
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
    op.create_index("ix_workspace_projects_workspace_id", "workspace_projects", ["workspace_id"])
    op.create_index(
        "ix_workspace_projects_workspace_updated",
        "workspace_projects",
        ["workspace_id", "updated_at"],
    )
    op.add_column("researches", sa.Column("project_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_researches_project_id",
        "researches",
        "workspace_projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_researches_project_id", "researches", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_researches_project_id", table_name="researches")
    op.drop_constraint("fk_researches_project_id", "researches", type_="foreignkey")
    op.drop_column("researches", "project_id")
    op.drop_index("ix_workspace_projects_workspace_updated", table_name="workspace_projects")
    op.drop_index("ix_workspace_projects_workspace_id", table_name="workspace_projects")
    op.drop_table("workspace_projects")
