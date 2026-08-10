"""add saved research configurations

Revision ID: 0059
Revises: 0058
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0059"
down_revision: str | None = "0058"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_research_configurations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("workspace_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("template_code", sa.String(100), nullable=False),
        sa.Column("routing_profile", sa.String(30), nullable=False),
        sa.Column("languages", sa.JSON(), nullable=False),
        sa.Column("regions", sa.JSON(), nullable=False),
        sa.Column("prompt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("schedule_hint", sa.String(100), nullable=True),
        sa.Column("configuration", sa.JSON(), nullable=False),
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
        sa.UniqueConstraint(
            "project_id", "name", name="uq_saved_research_config_name"
        ),
    )
    op.create_index(
        "ix_saved_research_configurations_project_id",
        "saved_research_configurations",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_saved_research_configurations_project_id",
        table_name="saved_research_configurations",
    )
    op.drop_table("saved_research_configurations")
