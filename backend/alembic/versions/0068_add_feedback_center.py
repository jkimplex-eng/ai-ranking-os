"""add feedback center

Revision ID: 0068
Revises: 0067
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0068"
down_revision: str | None = "0067"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("feedback_type", sa.String(30), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="NEW"),
        sa.Column("title", sa.String(250), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("research_id", sa.Integer(), nullable=True),
        sa.Column("report_id", sa.Integer(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
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
        "ix_product_feedback_status_priority", "product_feedback", ["status", "priority"]
    )
    op.create_index(
        "ix_product_feedback_user_created", "product_feedback", ["user_id", "created_at"]
    )
    op.create_table(
        "feedback_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "feedback_id",
            sa.Integer(),
            sa.ForeignKey("product_feedback.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_feedback_attachments_feedback_id", "feedback_attachments", ["feedback_id"])
    op.create_table(
        "feedback_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "feedback_id",
            sa.Integer(),
            sa.ForeignKey("product_feedback.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("old_state", sa.JSON(), nullable=True),
        sa.Column("new_state", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_feedback_history_feedback_id", "feedback_history", ["feedback_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_history_feedback_id", table_name="feedback_history")
    op.drop_table("feedback_history")
    op.drop_index("ix_feedback_attachments_feedback_id", table_name="feedback_attachments")
    op.drop_table("feedback_attachments")
    op.drop_index("ix_product_feedback_user_created", table_name="product_feedback")
    op.drop_index("ix_product_feedback_status_priority", table_name="product_feedback")
    op.drop_table("product_feedback")
