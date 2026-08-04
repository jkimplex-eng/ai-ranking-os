"""Add extensible segmentation definitions and snapshots.

Revision ID: 0030
Revises: 0029
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "segment_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("segment_type", sa.String(length=30), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
    op.create_index("uq_segment_definitions_code", "segment_definitions", ["code"], unique=True)
    op.create_index(
        "ix_segment_definitions_type_active", "segment_definitions", ["segment_type", "is_active"]
    )
    op.create_table(
        "segment_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "segment_id",
            sa.Integer(),
            sa.ForeignKey("segment_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("segment_version", sa.String(length=50), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("matched_count", sa.Integer(), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_segment_evaluations_segment_time",
        "segment_evaluations",
        ["segment_id", "evaluated_at"],
    )
    op.create_table(
        "segment_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "evaluation_id",
            sa.Integer(),
            sa.ForeignKey("segment_evaluations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("member_key", sa.String(length=64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
    )
    op.create_index("ix_segment_memberships_key", "segment_memberships", ["member_key"])
    op.create_index(
        "uq_segment_memberships_evaluation_key",
        "segment_memberships",
        ["evaluation_id", "member_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_segment_memberships_evaluation_key", table_name="segment_memberships")
    op.drop_index("ix_segment_memberships_key", table_name="segment_memberships")
    op.drop_table("segment_memberships")
    op.drop_index("ix_segment_evaluations_segment_time", table_name="segment_evaluations")
    op.drop_table("segment_evaluations")
    op.drop_index("ix_segment_definitions_type_active", table_name="segment_definitions")
    op.drop_index("uq_segment_definitions_code", table_name="segment_definitions")
    op.drop_table("segment_definitions")
