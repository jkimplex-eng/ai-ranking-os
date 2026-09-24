"""add competitor intelligence observations

Revision ID: 0079
Revises: 0078
"""

import sqlalchemy as sa
from alembic import op

revision = "0079"
down_revision = "0078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "competitor_daily_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "competitor_id",
            sa.Integer(),
            sa.ForeignKey("project_competitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("research_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mention_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommendation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "observed_visibility_score", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("algorithm_version", sa.String(length=30), nullable=False, server_default="1.0"),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "competitor_id", "snapshot_date", name="uq_competitor_snapshot_day"
        ),
    )
    op.create_index(
        "ix_competitor_snapshots_competitor_date",
        "competitor_daily_snapshots",
        ["competitor_id", "snapshot_date"],
    )
    op.create_table(
        "competitor_publication_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "competitor_id",
            sa.Integer(),
            sa.ForeignKey("project_competitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "research_id",
            sa.Integer(),
            sa.ForeignKey("researches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "response_id",
            sa.Integer(),
            sa.ForeignKey("research_responses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(length=253), nullable=False),
        sa.Column("title", sa.String(length=500)),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("mentioned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recommended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("excerpt", sa.Text()),
        sa.Column(
            "evidence_level",
            sa.String(length=30),
            nullable=False,
            server_default="OBSERVATION",
        ),
        sa.UniqueConstraint(
            "competitor_id", "response_id", "url", name="uq_competitor_publication_response"
        ),
    )
    op.create_index(
        "ix_competitor_publications_competitor_seen",
        "competitor_publication_observations",
        ["competitor_id", "last_seen_at"],
    )
    op.create_index(
        "ix_competitor_publications_domain",
        "competitor_publication_observations",
        ["domain"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_competitor_publications_domain",
        table_name="competitor_publication_observations",
    )
    op.drop_index(
        "ix_competitor_publications_competitor_seen",
        table_name="competitor_publication_observations",
    )
    op.drop_table("competitor_publication_observations")
    op.drop_index(
        "ix_competitor_snapshots_competitor_date",
        table_name="competitor_daily_snapshots",
    )
    op.drop_table("competitor_daily_snapshots")
