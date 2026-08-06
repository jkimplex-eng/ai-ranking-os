"""add product prompt and research template catalogs

Revision ID: 0042
Revises: 0041
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0042"
down_revision: str | None = "0041"
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
    prompts = op.create_table(
        "prompt_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("variables", sa.JSON(), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("code", "version", name="uq_prompt_definitions_code_version"),
    )
    op.create_index(
        "ix_prompt_definitions_category_language", "prompt_definitions", ["category", "language"]
    )
    templates = op.create_table(
        "research_template_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("prompt_code", sa.String(100), nullable=False),
        sa.Column("pipeline", sa.JSON(), nullable=False),
        sa.Column("default_languages", sa.JSON(), nullable=False),
        sa.Column("default_regions", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("code", "version", name="uq_research_templates_code_version"),
    )
    prompt_rows = []
    definitions = [
        ("ai-visibility", "AI Visibility", "Visibility"),
        ("brand-audit", "Brand Audit", "Brand"),
        ("product-audit", "Product Audit", "Product"),
        ("competitor-analysis", "Competitor Analysis", "Competitor"),
        ("reputation-analysis", "Reputation Analysis", "Reputation"),
        ("geo-analysis", "GEO Analysis", "GEO"),
    ]
    for code, title, category in definitions:
        prompt_rows.append(
            {
                "code": code,
                "version": 1,
                "title": title,
                "description": f"Deterministic {title} research prompt.",
                "category": category,
                "language": "en",
                "variables": ["brand", "language", "region"],
                "template": (
                    "Analyze the AI visibility of {brand} for language {language} "
                    "and region {region}. Name the brand explicitly, cite authoritative "
                    "sources, and provide ranked recommendations."
                ),
                "expected_output": {
                    "content": "string",
                    "citations": "array",
                    "recommendations": "array",
                },
                "tags": [category.casefold(), "mvp"],
                "status": "ACTIVE",
                "active": True,
            }
        )
    op.bulk_insert(prompts, prompt_rows)
    op.bulk_insert(
        templates,
        [
            {
                "code": code,
                "version": 1,
                "title": title,
                "description": f"Complete {title} pipeline.",
                "prompt_code": code,
                "pipeline": PIPELINE,
                "default_languages": ["en"],
                "default_regions": ["GLOBAL"],
                "active": True,
            }
            for code, title, _ in definitions
        ],
    )


def downgrade() -> None:
    op.drop_table("research_template_definitions")
    op.drop_index("ix_prompt_definitions_category_language", table_name="prompt_definitions")
    op.drop_table("prompt_definitions")
