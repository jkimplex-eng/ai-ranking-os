"""Add Research execution progress.

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "researches",
        sa.Column("total_tasks", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "researches",
        sa.Column("completed_tasks", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "researches",
        sa.Column("failed_tasks", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "researches",
        sa.Column("progress_percent", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "research_tasks",
        sa.Column("decision_task_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "research_tasks",
        sa.Column("execution_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "research_tasks",
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_research_tasks_decision_task_id",
        "research_tasks",
        "tasks",
        ["decision_task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_research_tasks_execution_id",
        "research_tasks",
        "executions",
        ["execution_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_research_tasks_decision_task_id",
        "research_tasks",
        ["decision_task_id"],
    )
    op.create_index(
        "ix_research_tasks_execution_id",
        "research_tasks",
        ["execution_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_research_tasks_execution_id",
        table_name="research_tasks",
    )
    op.drop_index(
        "ix_research_tasks_decision_task_id",
        table_name="research_tasks",
    )
    op.drop_constraint(
        "fk_research_tasks_execution_id",
        "research_tasks",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_research_tasks_decision_task_id",
        "research_tasks",
        type_="foreignkey",
    )
    op.drop_column("research_tasks", "error")
    op.drop_column("research_tasks", "execution_id")
    op.drop_column("research_tasks", "decision_task_id")
    op.drop_column("researches", "progress_percent")
    op.drop_column("researches", "failed_tasks")
    op.drop_column("researches", "completed_tasks")
    op.drop_column("researches", "total_tasks")
