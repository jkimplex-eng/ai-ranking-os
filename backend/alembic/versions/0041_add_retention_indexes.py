"""add retention indexes

Revision ID: 0041
Revises: 0040
"""

from collections.abc import Sequence

from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_execution_logs_created_at", "execution_logs", ["created_at"])
    op.create_index("ix_executions_state_finished_at", "executions", ["state", "finished_at"])
    op.create_index(
        "ix_query_execution_history_created_at", "query_execution_history", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_query_execution_history_created_at", table_name="query_execution_history")
    op.drop_index("ix_executions_state_finished_at", table_name="executions")
    op.drop_index("ix_execution_logs_created_at", table_name="execution_logs")
