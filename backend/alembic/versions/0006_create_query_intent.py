"""Create Query Intent Engine history.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intent_classification_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=200), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("primary_intent", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(
        "ix_intent_classification_runs_classified_at",
        "intent_classification_runs",
        ["classified_at"],
    )
    op.create_index(
        "ix_intent_classification_runs_language",
        "intent_classification_runs",
        ["language"],
    )
    op.create_index(
        "ix_intent_classification_runs_primary_intent",
        "intent_classification_runs",
        ["primary_intent"],
    )
    op.create_index(
        "ix_intent_classification_runs_request_id",
        "intent_classification_runs",
        ["request_id"],
        unique=True,
    )
    op.create_table(
        "intent_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=200), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=False),
        sa.Column("subtype", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("signals", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["intent_classification_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_intent_history_intent", "intent_history", ["intent"])
    op.create_index("ix_intent_history_request_id", "intent_history", ["request_id"])
    op.create_table(
        "confidence_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=200), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["intent_classification_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_confidence_history_intent", "confidence_history", ["intent"])
    op.create_index(
        "ix_confidence_history_request_id",
        "confidence_history",
        ["request_id"],
    )
    op.create_index("ix_confidence_history_source", "confidence_history", ["source"])
    op.create_table(
        "routing_metadata",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=200), nullable=False),
        sa.Column("strategy", sa.String(length=100), nullable=False),
        sa.Column("llm_fallback_required", sa.Boolean(), nullable=False),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["intent_classification_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_routing_metadata_request_id",
        "routing_metadata",
        ["request_id"],
    )
    op.create_index("ix_routing_metadata_strategy", "routing_metadata", ["strategy"])


def downgrade() -> None:
    op.drop_index("ix_routing_metadata_strategy", table_name="routing_metadata")
    op.drop_index("ix_routing_metadata_request_id", table_name="routing_metadata")
    op.drop_table("routing_metadata")
    op.drop_index("ix_confidence_history_source", table_name="confidence_history")
    op.drop_index("ix_confidence_history_request_id", table_name="confidence_history")
    op.drop_index("ix_confidence_history_intent", table_name="confidence_history")
    op.drop_table("confidence_history")
    op.drop_index("ix_intent_history_request_id", table_name="intent_history")
    op.drop_index("ix_intent_history_intent", table_name="intent_history")
    op.drop_table("intent_history")
    op.drop_index(
        "ix_intent_classification_runs_request_id",
        table_name="intent_classification_runs",
    )
    op.drop_index(
        "ix_intent_classification_runs_primary_intent",
        table_name="intent_classification_runs",
    )
    op.drop_index(
        "ix_intent_classification_runs_language",
        table_name="intent_classification_runs",
    )
    op.drop_index(
        "ix_intent_classification_runs_classified_at",
        table_name="intent_classification_runs",
    )
    op.drop_table("intent_classification_runs")

