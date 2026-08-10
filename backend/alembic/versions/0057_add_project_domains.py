"""add project domains and research domain binding

Revision ID: 0057
Revises: 0056
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0057"
down_revision: str | None = "0056"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_domains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("workspace_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("hostname", sa.String(253), nullable=False),
        sa.Column("display_name", sa.String(253), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("brands", sa.JSON(), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
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
        sa.UniqueConstraint("project_id", "hostname", name="uq_project_domains_hostname"),
    )
    op.create_index("ix_project_domains_project", "project_domains", ["project_id", "active"])
    op.create_index(
        "uq_project_domains_primary",
        "project_domains",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = true"),
        sqlite_where=sa.text("is_primary = 1"),
    )
    op.add_column("researches", sa.Column("domain_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_researches_domain_id",
        "researches",
        "project_domains",
        ["domain_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_researches_domain_id", "researches", ["domain_id"])


def downgrade() -> None:
    op.drop_index("ix_researches_domain_id", table_name="researches")
    op.drop_constraint("fk_researches_domain_id", "researches", type_="foreignkey")
    op.drop_column("researches", "domain_id")
    op.drop_index("uq_project_domains_primary", table_name="project_domains")
    op.drop_index("ix_project_domains_project", table_name="project_domains")
    op.drop_table("project_domains")
