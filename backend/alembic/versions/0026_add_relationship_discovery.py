"""Add relationship discovery candidates and evidence.

Revision ID: 0026
Revises: 0025
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "relationship_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("graph_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("source_external_id", sa.String(length=300), nullable=False),
        sa.Column("target_external_id", sa.String(length=300), nullable=False),
        sa.Column("relationship_type", sa.String(length=30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("algorithm_version", sa.String(length=50), nullable=False),
        sa.Column("integrated_snapshot_id", sa.Integer()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "uq_relationship_candidates_identity",
        "relationship_candidates",
        ["graph_snapshot_id", "source_external_id", "target_external_id", "relationship_type"],
        unique=True,
    )
    op.create_index(
        "ix_relationship_candidates_status_created",
        "relationship_candidates",
        ["status", "created_at"],
    )
    op.create_table(
        "relationship_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Integer(),
            sa.ForeignKey("relationship_candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_reference", sa.String(length=300), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_relationship_evidence_candidate", "relationship_evidence", ["candidate_id"])
    op.create_index(
        "uq_relationship_evidence_source",
        "relationship_evidence",
        ["candidate_id", "source_type", "source_reference"],
        unique=True,
    )
    op.create_table(
        "relationship_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Integer(),
            sa.ForeignKey("relationship_candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(length=20), nullable=False),
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
        "ix_relationship_decisions_candidate_created",
        "relationship_decisions",
        ["candidate_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_relationship_decisions_candidate_created", table_name="relationship_decisions"
    )
    op.drop_table("relationship_decisions")
    op.drop_index("uq_relationship_evidence_source", table_name="relationship_evidence")
    op.drop_index("ix_relationship_evidence_candidate", table_name="relationship_evidence")
    op.drop_table("relationship_evidence")
    op.drop_index("ix_relationship_candidates_status_created", table_name="relationship_candidates")
    op.drop_index("uq_relationship_candidates_identity", table_name="relationship_candidates")
    op.drop_table("relationship_candidates")
