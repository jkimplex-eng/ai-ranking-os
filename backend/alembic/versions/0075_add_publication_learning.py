"""add publication learning engine

Revision ID: 0075
Revises: 0074
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0075"
down_revision: str | None = "0074"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "research_publications",
        sa.Column("channel", sa.String(50), nullable=False, server_default="OWNED"),
    )
    op.add_column(
        "research_publications",
        sa.Column("content_type", sa.String(80), nullable=False, server_default="ARTICLE"),
    )
    op.add_column("research_publications", sa.Column("topic", sa.String(500)))
    op.add_column(
        "research_publications",
        sa.Column("target_queries", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "research_publications",
        sa.Column("metadata_payload", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_table(
        "publication_learning_experiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "publication_id",
            sa.Integer(),
            sa.ForeignKey("research_publications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column(
            "baseline_research_id",
            sa.Integer(),
            sa.ForeignKey("researches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "followup_research_id",
            sa.Integer(),
            sa.ForeignKey("researches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("matrix_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("causality_status", sa.String(40), nullable=False),
        sa.Column("evidence_grade", sa.String(20), nullable=False),
        sa.Column("metric_deltas", sa.JSON(), nullable=False),
        sa.Column("provider_deltas", sa.JSON(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("algorithm_version", sa.String(20), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "uq_publication_learning_experiment",
        "publication_learning_experiments",
        ["publication_id", "followup_research_id", "algorithm_version"],
        unique=True,
    )
    op.create_index(
        "ix_publication_learning_entity_evaluated",
        "publication_learning_experiments",
        ["entity_id", "evaluated_at"],
    )
    op.create_index(
        "ix_publication_learning_experiments_publication_id",
        "publication_learning_experiments",
        ["publication_id"],
    )
    op.create_index(
        "ix_publication_learning_experiments_entity_id",
        "publication_learning_experiments",
        ["entity_id"],
    )
    op.create_table(
        "publication_influence_estimates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource_domain", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("content_type", sa.String(80), nullable=False),
        sa.Column("metric", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("region", sa.String(20), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("expected_delta", sa.Float(), nullable=False),
        sa.Column("confidence_min", sa.Float(), nullable=False),
        sa.Column("confidence_max", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("evidence_grade", sa.String(20), nullable=False),
        sa.Column("algorithm_version", sa.String(20), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "uq_publication_influence_dimension",
        "publication_influence_estimates",
        [
            "resource_domain",
            "channel",
            "content_type",
            "metric",
            "provider",
            "model",
            "category",
            "language",
            "region",
            "algorithm_version",
        ],
        unique=True,
    )
    op.create_index(
        "ix_publication_influence_rank",
        "publication_influence_estimates",
        ["metric", "expected_delta", "confidence_score"],
    )


def downgrade() -> None:
    op.drop_table("publication_influence_estimates")
    op.drop_table("publication_learning_experiments")
    op.drop_column("research_publications", "metadata_payload")
    op.drop_column("research_publications", "target_queries")
    op.drop_column("research_publications", "topic")
    op.drop_column("research_publications", "content_type")
    op.drop_column("research_publications", "channel")
