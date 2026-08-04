"""add observability

Revision ID: 0037
Revises: 0036
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.create_table(
        "observability_spans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("span_id", sa.String(32), nullable=False, unique=True),
        sa.Column("operation", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_spans_trace_started", "observability_spans", ["trace_id", "started_at"])


def downgrade():
    op.drop_index("ix_spans_trace_started", table_name="observability_spans")
    op.drop_table("observability_spans")
