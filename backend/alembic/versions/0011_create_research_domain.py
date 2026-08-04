"""Create Research domain.

Revision ID: 0011
Revises: 0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

research_status = sa.Enum(
    "DRAFT",
    "ACTIVE",
    "COMPLETED",
    "ARCHIVED",
    name="research_status",
    native_enum=False,
    length=20,
)
research_task_status = sa.Enum(
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    name="research_task_status",
    native_enum=False,
    length=20,
)


def upgrade() -> None:
    op.create_table(
        "researches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("status", research_status, nullable=False),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_researches_status_created_at",
        "researches",
        ["status", "created_at"],
    )

    op.create_table(
        "research_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("research_id", sa.Integer(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("status", research_task_status, nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["research_id"],
            ["researches.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_research_tasks_research_id_status",
        "research_tasks",
        ["research_id", "status"],
    )

    op.create_table(
        "research_responses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["research_task_id"],
            ["research_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_research_responses_task_created_at",
        "research_responses",
        ["research_task_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_research_responses_task_created_at",
        table_name="research_responses",
    )
    op.drop_table("research_responses")
    op.drop_index(
        "ix_research_tasks_research_id_status",
        table_name="research_tasks",
    )
    op.drop_table("research_tasks")
    op.drop_index(
        "ix_researches_status_created_at",
        table_name="researches",
    )
    op.drop_table("researches")
