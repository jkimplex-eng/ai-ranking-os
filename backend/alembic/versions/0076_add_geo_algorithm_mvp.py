"""add GEO platform registry, frozen prompt sets, and heuristic EIS

Revision ID: 0076
Revises: 0075
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0076"
down_revision: str | None = "0075"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "geo_platforms",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("platform_type", sa.String(60), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("country", sa.String(8), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("source_reference", sa.Text()),
        sa.Column("ai_engines", sa.JSON(), nullable=False),
        sa.Column("domain_trust", sa.Float()),
        sa.Column("topical_authority_score", sa.Float()),
        sa.Column("ai_citation_history", sa.Integer()),
        sa.Column("allows_ai_crawlers", sa.Boolean()),
        sa.Column("in_knowledge_graph", sa.Boolean()),
        sa.Column("branded_mentions_90d", sa.Integer()),
        sa.Column("youtube_mentions", sa.Integer()),
        sa.Column("branded_anchors", sa.Integer()),
        sa.Column("branded_search_volume", sa.Float()),
        sa.Column("schema_markup_types", sa.JSON()),
        sa.Column("has_direct_answer", sa.Boolean()),
        sa.Column("content_freshness_days", sa.Integer()),
        sa.Column("has_structured_lists", sa.Boolean()),
        sa.Column("self_contained_paragraph_score", sa.Float()),
        sa.Column("cost_per_placement", sa.Numeric(14, 2)),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
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
    )
    op.create_index("uq_geo_platforms_domain", "geo_platforms", ["domain"], unique=True)
    op.create_index("ix_geo_platforms_category_language", "geo_platforms", ["category", "language"])
    op.create_table(
        "geo_platform_imports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("rows_total", sa.Integer(), nullable=False),
        sa.Column("rows_imported", sa.Integer(), nullable=False),
        sa.Column("rows_failed", sa.Integer(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_table(
        "frozen_prompt_sets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("region", sa.String(16), nullable=False),
        sa.Column("templates", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("frozen", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "uq_frozen_prompt_sets_code_version",
        "frozen_prompt_sets",
        ["code", "version"],
        unique=True,
    )
    op.create_index("ix_frozen_prompt_sets_active", "frozen_prompt_sets", ["code", "active"])
    op.create_table(
        "frozen_prompt_instances",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "prompt_set_id",
            sa.Uuid(),
            sa.ForeignKey("frozen_prompt_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stable_key", sa.String(64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("query_type", sa.String(40), nullable=False),
        sa.Column("variables", sa.JSON(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "uq_frozen_prompt_instance_key",
        "frozen_prompt_instances",
        ["prompt_set_id", "stable_key"],
        unique=True,
    )
    op.create_index(
        "ix_frozen_prompt_instances_type",
        "frozen_prompt_instances",
        ["prompt_set_id", "query_type"],
    )
    op.create_table(
        "eis_scores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "platform_id",
            sa.Uuid(),
            sa.ForeignKey("geo_platforms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "query_id",
            sa.Uuid(),
            sa.ForeignKey("frozen_prompt_instances.id", ondelete="SET NULL"),
        ),
        sa.Column("ai_engine", sa.String(60), nullable=False),
        sa.Column("model_type", sa.String(30), nullable=False),
        sa.Column("eis_value", sa.Float()),
        sa.Column("priority", sa.String(8)),
        sa.Column("components", sa.JSON(), nullable=False),
        sa.Column("signal_probabilities", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("evidence_status", sa.String(30), nullable=False),
        sa.Column("methodology_version", sa.String(30), nullable=False),
        sa.Column("weight_set_version", sa.String(30), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_eis_scores_platform_calculated", "eis_scores", ["platform_id", "calculated_at"]
    )
    op.create_index("ix_eis_scores_priority_value", "eis_scores", ["priority", "eis_value"])


def downgrade() -> None:
    op.drop_table("eis_scores")
    op.drop_table("frozen_prompt_instances")
    op.drop_table("frozen_prompt_sets")
    op.drop_table("geo_platform_imports")
    op.drop_table("geo_platforms")
