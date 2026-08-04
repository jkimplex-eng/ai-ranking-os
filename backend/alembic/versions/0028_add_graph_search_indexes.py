"""Add graph search indexes.

Revision ID: 0028
Revises: 0027
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_graph_nodes_snapshot_name", "graph_nodes", ["snapshot_id", "name"])
    op.create_index(
        "ix_graph_nodes_snapshot_canonical",
        "graph_nodes",
        ["snapshot_id", "canonical_name"],
    )
    op.create_index(
        "ix_graph_edges_snapshot_target",
        "graph_edges",
        ["snapshot_id", "target_node_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_graph_edges_snapshot_target", table_name="graph_edges")
    op.drop_index("ix_graph_nodes_snapshot_canonical", table_name="graph_nodes")
    op.drop_index("ix_graph_nodes_snapshot_name", table_name="graph_nodes")
