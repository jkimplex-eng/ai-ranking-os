"""Create Execution Engine.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

task_priority = sa.Enum(
    "HIGH",
    "MEDIUM",
    "LOW",
    name="task_priority",
    native_enum=False,
    length=10,
)
agent_type = sa.Enum(
    "CODEX",
    "QWEN",
    "DEEPSEEK",
    "CLAUDE",
    "GEMINI",
    name="agent_type",
    native_enum=False,
    length=20,
)
execution_state = sa.Enum(
    "PENDING",
    "ASSIGNED",
    "RUNNING",
    "WAITING_REVIEW",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    name="execution_state",
    native_enum=False,
    length=20,
)


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column(
            "agent_type",
            agent_type,
            server_default="CODEX",
            nullable=False,
        ),
    )
    op.add_column("agents", sa.Column("specialization", sa.String(length=100), nullable=True))
    op.add_column(
        "agents",
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_index("ix_agents_specialization", "agents", ["specialization"])

    op.add_column(
        "tasks",
        sa.Column(
            "priority",
            task_priority,
            server_default="MEDIUM",
            nullable=False,
        ),
    )
    op.add_column(
        "tasks",
        sa.Column("required_specialization", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_tasks_required_specialization",
        "tasks",
        ["required_specialization"],
    )

    op.create_table(
        "executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column(
            "state",
            execution_state,
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_executions_agent_id", "executions", ["agent_id"])
    op.create_index("ix_executions_state", "executions", ["state"])
    op.create_index("ix_executions_task_id", "executions", ["task_id"])
    op.create_index(
        "uq_executions_active_task",
        "executions",
        ["task_id"],
        unique=True,
        postgresql_where=sa.text(
            "state IN ('PENDING', 'ASSIGNED', 'RUNNING', 'WAITING_REVIEW')"
        ),
        sqlite_where=sa.text(
            "state IN ('PENDING', 'ASSIGNED', 'RUNNING', 'WAITING_REVIEW')"
        ),
    )
    op.create_index(
        "uq_executions_active_agent",
        "executions",
        ["agent_id"],
        unique=True,
        postgresql_where=sa.text(
            "state IN ('ASSIGNED', 'RUNNING', 'WAITING_REVIEW') "
            "AND agent_id IS NOT NULL"
        ),
        sqlite_where=sa.text(
            "state IN ('ASSIGNED', 'RUNNING', 'WAITING_REVIEW') "
            "AND agent_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_executions_active_agent", table_name="executions")
    op.drop_index("uq_executions_active_task", table_name="executions")
    op.drop_index("ix_executions_task_id", table_name="executions")
    op.drop_index("ix_executions_state", table_name="executions")
    op.drop_index("ix_executions_agent_id", table_name="executions")
    op.drop_table("executions")

    op.drop_index("ix_tasks_required_specialization", table_name="tasks")
    op.drop_column("tasks", "required_specialization")
    op.drop_column("tasks", "priority")

    op.drop_index("ix_agents_specialization", table_name="agents")
    op.drop_column("agents", "is_enabled")
    op.drop_column("agents", "specialization")
    op.drop_column("agents", "agent_type")

