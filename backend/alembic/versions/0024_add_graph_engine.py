"""Add immutable knowledge graph snapshots.

Revision ID: 0024
Revises: 0023
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "graph_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("structure_version", sa.String(length=50), nullable=False),
        sa.Column("node_count", sa.Integer(), nullable=False),
        sa.Column("edge_count", sa.Integer(), nullable=False),
        sa.Column("build_metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
    )
    op.create_index("ix_graph_snapshots_created", "graph_snapshots", ["created_at"])
    op.create_table(
        "graph_nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "snapshot_id", sa.Integer(),
            sa.ForeignKey("graph_snapshots.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("external_id", sa.String(length=300), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("canonical_name", sa.String(length=500), nullable=False),
        sa.Column("node_type", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
    )
    op.create_index(
        "uq_graph_nodes_snapshot_external", "graph_nodes",
        ["snapshot_id", "external_id"], unique=True,
    )
    op.create_index(
        "ix_graph_nodes_snapshot_type", "graph_nodes", ["snapshot_id", "node_type"]
    )
    op.create_table(
        "graph_edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "snapshot_id", sa.Integer(),
            sa.ForeignKey("graph_snapshots.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "source_node_id", sa.Integer(),
            sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "target_node_id", sa.Integer(),
            sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("edge_type", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_graph_edges_snapshot_type", "graph_edges", ["snapshot_id", "edge_type"]
    )
    op.create_index(
        "uq_graph_edges_snapshot_nodes_type", "graph_edges",
        ["snapshot_id", "source_node_id", "target_node_id", "edge_type"], unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_graph_edges_snapshot_nodes_type", table_name="graph_edges")
    op.drop_index("ix_graph_edges_snapshot_type", table_name="graph_edges")
    op.drop_table("graph_edges")
    op.drop_index("ix_graph_nodes_snapshot_type", table_name="graph_nodes")
    op.drop_index("uq_graph_nodes_snapshot_external", table_name="graph_nodes")
    op.drop_table("graph_nodes")
    op.drop_index("ix_graph_snapshots_created", table_name="graph_snapshots")
    op.drop_table("graph_snapshots")

