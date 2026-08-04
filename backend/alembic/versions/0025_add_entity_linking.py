"""Add canonical entity linking and decision history.

Revision ID: 0025
Revises: 0024
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canonical_entities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_name", sa.String(length=500), nullable=False),
        sa.Column("normalized_name", sa.String(length=500), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("algorithm_version", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "uq_canonical_entities_type_normalized",
        "canonical_entities",
        ["entity_type", "normalized_name"],
        unique=True,
    )
    op.create_table(
        "entity_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "canonical_entity_id",
            sa.Integer(),
            sa.ForeignKey("canonical_entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(length=500), nullable=False),
        sa.Column("normalized_alias", sa.String(length=500), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_entity_aliases_canonical_id", "entity_aliases", ["canonical_entity_id"])
    op.create_index(
        "uq_entity_aliases_type_normalized",
        "entity_aliases",
        ["entity_type", "normalized_alias"],
        unique=True,
    )
    op.create_table(
        "link_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("graph_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("graph_node_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=300), nullable=False),
        sa.Column("entity_name", sa.String(length=500), nullable=False),
        sa.Column("normalized_name", sa.String(length=500), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column(
            "canonical_entity_id",
            sa.Integer(),
            sa.ForeignKey("canonical_entities.id", ondelete="SET NULL"),
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("match_method", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("algorithm_version", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_link_candidates_status_created", "link_candidates", ["status", "created_at"]
    )
    op.create_index(
        "ix_link_candidates_snapshot_node",
        "link_candidates",
        ["graph_snapshot_id", "graph_node_id"],
    )
    op.create_table(
        "link_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Integer(),
            sa.ForeignKey("link_candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("canonical_entity_id", sa.Integer()),
        sa.Column("actor", sa.String(length=100), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("algorithm_version", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_link_decisions_candidate_created", "link_decisions", ["candidate_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_link_decisions_candidate_created", table_name="link_decisions")
    op.drop_table("link_decisions")
    op.drop_index("ix_link_candidates_snapshot_node", table_name="link_candidates")
    op.drop_index("ix_link_candidates_status_created", table_name="link_candidates")
    op.drop_table("link_candidates")
    op.drop_index("uq_entity_aliases_type_normalized", table_name="entity_aliases")
    op.drop_index("ix_entity_aliases_canonical_id", table_name="entity_aliases")
    op.drop_table("entity_aliases")
    op.drop_index("uq_canonical_entities_type_normalized", table_name="canonical_entities")
    op.drop_table("canonical_entities")
