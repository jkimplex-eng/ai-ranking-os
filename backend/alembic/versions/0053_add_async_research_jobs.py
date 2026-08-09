"""add durable async research queue

Revision ID: 0053
Revises: 0052
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0053"
down_revision: str | None = "0052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "research_id",
            sa.Integer(),
            sa.ForeignKey("researches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_research_jobs_research_id", "research_jobs", ["research_id"])
    op.create_index("ix_research_jobs_state", "research_jobs", ["state"])
    op.create_index("ix_research_jobs_state_created", "research_jobs", ["state", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_research_jobs_state_created", table_name="research_jobs")
    op.drop_index("ix_research_jobs_state", table_name="research_jobs")
    op.drop_index("ix_research_jobs_research_id", table_name="research_jobs")
    op.drop_table("research_jobs")
