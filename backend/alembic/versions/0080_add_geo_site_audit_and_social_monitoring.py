"""add GEO site audit and competitor social monitoring

Revision ID: 0080
Revises: 0079
"""

import sqlalchemy as sa
from alembic import op

revision = "0080"
down_revision = "0079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "geo_site_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "project_id", sa.Integer(), sa.ForeignKey("workspace_projects.id", ondelete="CASCADE")
        ),
        sa.Column("brand", sa.String(200), nullable=False),
        sa.Column("website_url", sa.Text(), nullable=False),
        sa.Column("final_url", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("grade", sa.String(30), nullable=False),
        sa.Column("category_scores", sa.JSON(), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("opportunities", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("algorithm_version", sa.String(30), nullable=False, server_default="1.0"),
        sa.Column("limitation", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_geo_site_audits_user_id", "geo_site_audits", ["user_id"])
    op.create_index(
        "ix_geo_site_audits_project_created", "geo_site_audits", ["project_id", "created_at"]
    )
    op.create_table(
        "competitor_social_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "competitor_id",
            sa.Integer(),
            sa.ForeignKey("project_competitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(30), nullable=False),
        sa.Column("profile_url", sa.Text(), nullable=False),
        sa.Column("external_id", sa.String(300), nullable=False),
        sa.Column("encrypted_token", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True)),
        sa.Column("next_scan_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
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
        sa.UniqueConstraint(
            "competitor_id", "platform", "external_id", name="uq_competitor_social_source"
        ),
    )
    op.create_index(
        "ix_competitor_social_sources_due", "competitor_social_sources", ["active", "next_scan_at"]
    )
    op.create_table(
        "competitor_social_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("competitor_social_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_post_id", sa.String(300), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(500)),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("views", sa.Integer()),
        sa.Column("likes", sa.Integer()),
        sa.Column("comments", sa.Integer()),
        sa.Column("shares", sa.Integer()),
        sa.Column("engagement_rate", sa.Float()),
        sa.Column("significance_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("raw_metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("source_id", "external_post_id", name="uq_competitor_social_post"),
    )
    op.create_index(
        "ix_competitor_social_posts_source_published",
        "competitor_social_posts",
        ["source_id", "published_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_competitor_social_posts_source_published", table_name="competitor_social_posts"
    )
    op.drop_table("competitor_social_posts")
    op.drop_index("ix_competitor_social_sources_due", table_name="competitor_social_sources")
    op.drop_table("competitor_social_sources")
    op.drop_index("ix_geo_site_audits_project_created", table_name="geo_site_audits")
    op.drop_index("ix_geo_site_audits_user_id", table_name="geo_site_audits")
    op.drop_table("geo_site_audits")
