"""Create Entity Extraction Engine history.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "entity_extraction_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("response_id", sa.String(length=200), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("response_id"),
    )
    op.create_index(
        "ix_entity_extraction_runs_processed_at",
        "entity_extraction_runs",
        ["processed_at"],
    )
    op.create_index(
        "ix_entity_extraction_runs_response_id",
        "entity_extraction_runs",
        ["response_id"],
        unique=True,
    )
    op.create_table(
        "entity_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("response_id", sa.String(length=200), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("canonical_name", sa.String(length=500), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("knowledge_graph_id", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["entity_extraction_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entity_history_canonical_name", "entity_history", ["canonical_name"])
    op.create_index("ix_entity_history_entity_type", "entity_history", ["entity_type"])
    op.create_index(
        "ix_entity_history_knowledge_graph_id",
        "entity_history",
        ["knowledge_graph_id"],
    )
    op.create_index("ix_entity_history_response_id", "entity_history", ["response_id"])
    op.create_table(
        "relation_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("response_id", sa.String(length=200), nullable=False),
        sa.Column("relation_id", sa.String(length=100), nullable=False),
        sa.Column("source_entity_id", sa.String(length=100), nullable=False),
        sa.Column("target_entity_id", sa.String(length=100), nullable=False),
        sa.Column("relation_type", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["entity_extraction_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_relation_history_relation_type",
        "relation_history",
        ["relation_type"],
    )
    op.create_index("ix_relation_history_response_id", "relation_history", ["response_id"])
    op.create_table(
        "resolution_log_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("response_id", sa.String(length=200), nullable=False),
        sa.Column("stage", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["entity_extraction_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resolution_log_history_response_id",
        "resolution_log_history",
        ["response_id"],
    )
    op.create_index(
        "ix_resolution_log_history_stage",
        "resolution_log_history",
        ["stage"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resolution_log_history_stage",
        table_name="resolution_log_history",
    )
    op.drop_index(
        "ix_resolution_log_history_response_id",
        table_name="resolution_log_history",
    )
    op.drop_table("resolution_log_history")
    op.drop_index("ix_relation_history_response_id", table_name="relation_history")
    op.drop_index("ix_relation_history_relation_type", table_name="relation_history")
    op.drop_table("relation_history")
    op.drop_index("ix_entity_history_response_id", table_name="entity_history")
    op.drop_index(
        "ix_entity_history_knowledge_graph_id",
        table_name="entity_history",
    )
    op.drop_index("ix_entity_history_entity_type", table_name="entity_history")
    op.drop_index("ix_entity_history_canonical_name", table_name="entity_history")
    op.drop_table("entity_history")
    op.drop_index(
        "ix_entity_extraction_runs_response_id",
        table_name="entity_extraction_runs",
    )
    op.drop_index(
        "ix_entity_extraction_runs_processed_at",
        table_name="entity_extraction_runs",
    )
    op.drop_table("entity_extraction_runs")

