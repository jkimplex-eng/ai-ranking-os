"""Create rule-based Recommendation Engine.

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    rules = op.create_table(
        "recommendation_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=100), nullable=False, unique=True),
        sa.Column("recommendation_type", sa.String(length=100), nullable=False),
        sa.Column("metric", sa.String(length=100), nullable=False),
        sa.Column("operator", sa.String(length=20), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("explanation_template", sa.Text(), nullable=False),
        sa.Column("expected_effect", sa.Text(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_recommendation_rules_active_version",
        "recommendation_rules",
        ["is_active", "version"],
    )
    op.create_table(
        "recommendation_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("research_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("engine_version", sa.String(length=50), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("generated_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_recommendation_executions_research_started",
        "recommendation_executions",
        ["research_id", "started_at"],
    )
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "execution_id",
            sa.Integer(),
            sa.ForeignKey("recommendation_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rule_id",
            sa.Integer(),
            sa.ForeignKey("recommendation_rules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("research_id", sa.Integer(), nullable=False),
        sa.Column("recommendation_type", sa.String(length=100), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("metric", sa.String(length=100), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("expected_effect", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_recommendations_research_created",
        "recommendations",
        ["research_id", "created_at"],
    )
    op.create_index(
        "ix_recommendations_execution_priority",
        "recommendations",
        ["execution_id", "priority"],
    )
    op.create_index(
        "ix_recommendations_rule_id",
        "recommendations",
        ["rule_id"],
    )
    op.bulk_insert(rules, _default_rules())


def downgrade() -> None:
    op.drop_index(
        "ix_recommendations_rule_id",
        table_name="recommendations",
    )
    op.drop_index(
        "ix_recommendations_execution_priority",
        table_name="recommendations",
    )
    op.drop_index(
        "ix_recommendations_research_created",
        table_name="recommendations",
    )
    op.drop_table("recommendations")
    op.drop_index(
        "ix_recommendation_executions_research_started",
        table_name="recommendation_executions",
    )
    op.drop_table("recommendation_executions")
    op.drop_index(
        "ix_recommendation_rules_active_version",
        table_name="recommendation_rules",
    )
    op.drop_table("recommendation_rules")


def _default_rules() -> list[dict]:
    return [
        {
            "code": "v1-low-mention",
            "recommendation_type": "MENTION_GROWTH",
            "metric": "mention_score",
            "operator": "lt",
            "threshold": 60.0,
            "priority": "HIGH",
            "explanation_template": (
                "Mention Score {metric_value} is below {threshold}. "
                "Increase the number of relevant, high-quality mentions."
            ),
            "expected_effect": "Raise Mention Score to at least 60.",
            "version": "1.0",
            "is_active": True,
        },
        {
            "code": "v1-low-citation",
            "recommendation_type": "CITATION_AUTHORITY",
            "metric": "citation_score",
            "operator": "lt",
            "threshold": 50.0,
            "priority": "HIGH",
            "explanation_template": (
                "Citation Score {metric_value} is below {threshold}. "
                "Add more authoritative and independently verifiable sources."
            ),
            "expected_effect": "Raise Citation Score to at least 50.",
            "version": "1.0",
            "is_active": True,
        },
        {
            "code": "v1-low-recommendation",
            "recommendation_type": "TRUST_SIGNALS",
            "metric": "recommendation_score",
            "operator": "lt",
            "threshold": 60.0,
            "priority": "CRITICAL",
            "explanation_template": (
                "Recommendation Score {metric_value} is below {threshold}. "
                "Strengthen evidence, reviews, and trust signals."
            ),
            "expected_effect": "Raise Recommendation Score to at least 60.",
            "version": "1.0",
            "is_active": True,
        },
        {
            "code": "v1-low-coverage",
            "recommendation_type": "SOURCE_EXPANSION",
            "metric": "coverage_score",
            "operator": "lt",
            "threshold": 70.0,
            "priority": "MEDIUM",
            "explanation_template": (
                "Coverage Score {metric_value} is below {threshold}. "
                "Expand presence across additional models and sources."
            ),
            "expected_effect": "Raise Coverage Score to at least 70.",
            "version": "1.0",
            "is_active": True,
        },
    ]
