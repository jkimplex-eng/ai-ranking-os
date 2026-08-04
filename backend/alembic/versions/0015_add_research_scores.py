"""Add Research visibility scores.

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "research_id",
            sa.Integer(),
            sa.ForeignKey("researches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mention_score", sa.Float(), nullable=False),
        sa.Column("recommendation_score", sa.Float(), nullable=False),
        sa.Column("citation_score", sa.Float(), nullable=False),
        sa.Column("coverage_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("visibility_score", sa.Float(), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("version", sa.String(length=50), nullable=False),
    )
    op.create_index(
        "uq_research_scores_research_version",
        "research_scores",
        ["research_id", "version"],
        unique=True,
    )
    op.create_index(
        "ix_research_scores_calculated_at",
        "research_scores",
        ["calculated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_research_scores_calculated_at",
        table_name="research_scores",
    )
    op.drop_index(
        "uq_research_scores_research_version",
        table_name="research_scores",
    )
    op.drop_table("research_scores")
