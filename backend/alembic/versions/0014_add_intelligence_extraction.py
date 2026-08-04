"""Add Research intelligence extraction.

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "research_responses",
        sa.Column(
            "processing_status",
            sa.String(length=20),
            server_default="NORMALIZED",
            nullable=False,
        ),
    )
    op.add_column(
        "research_responses",
        sa.Column("processing_error", sa.Text(), nullable=True),
    )
    op.create_table(
        "research_extracted_entities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "response_id",
            sa.Integer(),
            sa.ForeignKey("research_responses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("canonical_name", sa.String(length=500), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("knowledge_graph_id", sa.String(length=100), nullable=True),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_research_entities_response_type",
        "research_extracted_entities",
        ["response_id", "entity_type"],
    )
    op.create_table(
        "research_extracted_citations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "response_id",
            sa.Integer(),
            sa.ForeignKey("research_responses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("source", sa.String(length=300), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_research_citations_response",
        "research_extracted_citations",
        ["response_id"],
    )
    op.create_table(
        "research_extracted_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "response_id",
            sa.Integer(),
            sa.ForeignKey("research_responses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_research_recommendations_response",
        "research_extracted_recommendations",
        ["response_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_research_recommendations_response",
        table_name="research_extracted_recommendations",
    )
    op.drop_table("research_extracted_recommendations")
    op.drop_index(
        "ix_research_citations_response",
        table_name="research_extracted_citations",
    )
    op.drop_table("research_extracted_citations")
    op.drop_index(
        "ix_research_entities_response_type",
        table_name="research_extracted_entities",
    )
    op.drop_table("research_extracted_entities")
    op.drop_column("research_responses", "processing_error")
    op.drop_column("research_responses", "processing_status")
