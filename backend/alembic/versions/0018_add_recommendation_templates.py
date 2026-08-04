"""Add versioned Recommendation templates.

Revision ID: 0018
Revises: 0017
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    templates = op.create_table(
        "recommendation_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_code", sa.String(length=100), nullable=False),
        sa.Column("recommendation_type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("expected_result", sa.Text(), nullable=False),
        sa.Column("estimated_time", sa.String(length=100), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "template_code",
            "version",
            name="uq_recommendation_templates_code_version",
        ),
    )
    op.create_index(
        "ix_recommendation_templates_type_version",
        "recommendation_templates",
        ["recommendation_type", "version"],
    )
    op.add_column(
        "recommendations",
        sa.Column("template_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_recommendations_template_id",
        "recommendations",
        "recommendation_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_recommendations_template_id",
        "recommendations",
        ["template_id"],
    )
    for values in _default_templates():
        row = dict(values)
        steps = row.pop("steps")
        op.execute(
            templates.insert().values(
                **row,
                steps=sa.cast(
                    op.inline_literal(json.dumps(steps)),
                    sa.JSON(),
                ),
            )
        )


def downgrade() -> None:
    op.drop_index(
        "ix_recommendations_template_id",
        table_name="recommendations",
    )
    op.drop_constraint(
        "fk_recommendations_template_id",
        "recommendations",
        type_="foreignkey",
    )
    op.drop_column("recommendations", "template_id")
    op.drop_index(
        "ix_recommendation_templates_type_version",
        table_name="recommendation_templates",
    )
    op.drop_table("recommendation_templates")


def _default_templates() -> list[dict]:
    return [
        {
            "template_code": "mention-quality-plan",
            "recommendation_type": "MENTION_GROWTH",
            "title": "Increase high-quality entity mentions",
            "description": "Build consistent, attributable mentions in relevant sources.",
            "steps": [
                "Audit current mentions and identify missing authoritative sources.",
                "Prepare consistent entity descriptions and factual proof points.",
                "Publish or update content in the highest-priority sources.",
                "Repeat the research and compare Mention Score.",
            ],
            "expected_result": "More frequent and consistent entity mentions.",
            "estimated_time": "2-4 weeks",
            "priority": "HIGH",
            "version": "1.0",
        },
        {
            "template_code": "citation-authority-plan",
            "recommendation_type": "CITATION_AUTHORITY",
            "title": "Strengthen authoritative citations",
            "description": "Increase independently verifiable, trusted references.",
            "steps": [
                "Map existing citations and authority gaps.",
                "Create evidence assets with stable URLs and clear authorship.",
                "Secure references from reputable independent publications.",
                "Validate citation discovery in a follow-up research run.",
            ],
            "expected_result": "Higher citation frequency and source authority.",
            "estimated_time": "3-6 weeks",
            "priority": "HIGH",
            "version": "1.0",
        },
        {
            "template_code": "trust-signals-plan",
            "recommendation_type": "TRUST_SIGNALS",
            "title": "Improve recommendation trust signals",
            "description": "Make quality, proof, and third-party validation explicit.",
            "steps": [
                "Inventory reviews, certifications, case studies, and guarantees.",
                "Resolve inconsistent claims across owned properties.",
                "Publish evidence-backed comparisons and customer outcomes.",
                "Measure Recommendation Score after signals are indexed.",
            ],
            "expected_result": "Stronger evidence supporting model recommendations.",
            "estimated_time": "2-5 weeks",
            "priority": "CRITICAL",
            "version": "1.0",
        },
        {
            "template_code": "source-expansion-plan",
            "recommendation_type": "SOURCE_EXPANSION",
            "title": "Expand model and source coverage",
            "description": "Increase presence across sources used by additional models.",
            "steps": [
                "Identify models and source categories with no current presence.",
                "Prioritize sources shared by multiple target models.",
                "Publish localized or domain-specific entity content.",
                "Run a cross-model research comparison.",
            ],
            "expected_result": "Broader cross-model and cross-source coverage.",
            "estimated_time": "3-8 weeks",
            "priority": "MEDIUM",
            "version": "1.0",
        },
    ]
