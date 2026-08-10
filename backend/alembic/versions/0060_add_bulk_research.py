"""add bulk research runs

Revision ID: 0060
Revises: 0059
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0060"
down_revision: str | None = "0059"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bulk_research_runs",
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
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_bulk_research_runs_project_id", "bulk_research_runs", ["project_id"]
    )
    op.create_table(
        "bulk_research_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bulk_run_id",
            sa.Integer(),
            sa.ForeignKey("bulk_research_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("brand", sa.String(200), nullable=False),
        sa.Column(
            "domain_id",
            sa.Integer(),
            sa.ForeignKey("project_domains.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("research_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("job_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "bulk_run_id", "brand", name="uq_bulk_research_item_brand"
        ),
    )
    op.create_index(
        "ix_bulk_research_items_bulk_run_id", "bulk_research_items", ["bulk_run_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_bulk_research_items_bulk_run_id", table_name="bulk_research_items"
    )
    op.drop_table("bulk_research_items")
    op.drop_index("ix_bulk_research_runs_project_id", table_name="bulk_research_runs")
    op.drop_table("bulk_research_runs")
