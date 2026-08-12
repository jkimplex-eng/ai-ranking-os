"""add research laboratory publication provenance

Revision ID: 0072
Revises: 0071
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0072"
down_revision: str | None = "0071"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_publications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("research_id", sa.Integer(), sa.ForeignKey("researches.id", ondelete="SET NULL")),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_research_publications_entity_id", "research_publications", ["entity_id"])
    op.create_index(
        "ix_research_publications_research_id", "research_publications", ["research_id"]
    )
    op.create_index(
        "ix_research_publications_entity_published",
        "research_publications",
        ["entity_id", "published_at"],
    )
    op.create_table(
        "publication_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "publication_id",
            sa.Integer(),
            sa.ForeignKey("research_publications.id", ondelete="CASCADE"),
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
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_excerpt", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_publication_observations_research_id", "publication_observations", ["research_id"]
    )
    op.create_index(
        "ix_publication_observations_response_id", "publication_observations", ["response_id"]
    )
    op.create_index(
        "ix_publication_observations_first_observed",
        "publication_observations",
        ["first_observed_at"],
    )
    op.create_index(
        "uq_publication_observation_provider_model",
        "publication_observations",
        ["publication_id", "provider", "model"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("publication_observations")
    op.drop_table("research_publications")
