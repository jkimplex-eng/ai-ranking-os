"""extend research templates for product readiness

Revision ID: 0058
Revises: 0057
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0058"
down_revision: str | None = "0057"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PIPELINE = [
    "provider",
    "normalization",
    "extraction",
    "knowledge_graph",
    "scoring",
    "recommendations",
    "analytics",
    "insights",
    "report",
]


def upgrade() -> None:
    op.add_column(
        "research_template_definitions",
        sa.Column(
            "research_type",
            sa.String(60),
            server_default="BRAND_VISIBILITY",
            nullable=False,
        ),
    )
    op.add_column(
        "research_template_definitions",
        sa.Column("configuration", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
    )
    mappings = {
        "ai-visibility": "BRAND_VISIBILITY",
        "brand-audit": "BRAND_VISIBILITY",
        "product-audit": "PRODUCT_AUDIT",
        "competitor-analysis": "COMPETITOR_COMPARISON",
        "reputation-analysis": "AI_RECOMMENDATION_AUDIT",
        "geo-analysis": "GEO_AUDIT",
    }
    for code, research_type in mappings.items():
        op.execute(
            sa.text(
                "UPDATE research_template_definitions "
                "SET research_type = :research_type WHERE code = :code"
            ).bindparams(code=code, research_type=research_type)
        )
    table = sa.table(
        "research_template_definitions",
        sa.column("code", sa.String),
        sa.column("version", sa.Integer),
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("research_type", sa.String),
        sa.column("prompt_code", sa.String),
        sa.column("pipeline", sa.JSON),
        sa.column("default_languages", sa.JSON),
        sa.column("default_regions", sa.JSON),
        sa.column("configuration", sa.JSON),
        sa.column("active", sa.Boolean),
    )
    op.bulk_insert(
        table,
        [
            {
                "code": code,
                "version": 1,
                "title": title,
                "description": f"Daily-ready {title} pipeline.",
                "research_type": research_type,
                "prompt_code": "ai-visibility",
                "pipeline": PIPELINE,
                "default_languages": ["ru", "en"],
                "default_regions": ["GLOBAL"],
                "configuration": {"routing_profile": "BALANCED"},
                "active": True,
            }
            for code, title, research_type in (
                ("ai-recommendation-audit", "AI Recommendation Audit", "AI_RECOMMENDATION_AUDIT"),
                ("content-audit", "Content Audit", "CONTENT_AUDIT"),
                ("website-audit", "Website Audit", "WEBSITE_AUDIT"),
            )
        ],
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM research_template_definitions "
        "WHERE code IN ('ai-recommendation-audit', 'content-audit', 'website-audit')"
    )
    op.drop_column("research_template_definitions", "configuration")
    op.drop_column("research_template_definitions", "research_type")
