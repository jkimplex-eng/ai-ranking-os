"""Add versioned entity influence scoring.

Revision ID: 0027
Revises: 0026
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "influence_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("graph_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=50), nullable=False),
        sa.Column("node_count", sa.Integer(), nullable=False),
        sa.Column("edge_count", sa.Integer(), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "graph_snapshot_id",
            "algorithm_version",
            name="uq_influence_snapshot_graph_version",
        ),
    )
    op.create_index("ix_influence_snapshots_calculated", "influence_snapshots", ["calculated_at"])
    op.create_table(
        "entity_influence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.Integer(),
            sa.ForeignKey("influence_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_id", sa.String(length=300), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("node_type", sa.String(length=100), nullable=False),
        sa.Column("degree", sa.Float(), nullable=False),
        sa.Column("weighted_degree", sa.Float(), nullable=False),
        sa.Column("pagerank", sa.Float(), nullable=False),
        sa.Column("betweenness", sa.Float(), nullable=False),
        sa.Column("closeness", sa.Float(), nullable=False),
        sa.Column("influence_score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.UniqueConstraint("snapshot_id", "entity_id", name="uq_entity_influence_snapshot_entity"),
    )
    op.create_index("ix_entity_influence_entity", "entity_influence", ["entity_id"])
    op.create_index(
        "ix_entity_influence_snapshot_rank", "entity_influence", ["snapshot_id", "rank"]
    )


def downgrade() -> None:
    op.drop_index("ix_entity_influence_snapshot_rank", table_name="entity_influence")
    op.drop_index("ix_entity_influence_entity", table_name="entity_influence")
    op.drop_table("entity_influence")
    op.drop_index("ix_influence_snapshots_calculated", table_name="influence_snapshots")
    op.drop_table("influence_snapshots")
