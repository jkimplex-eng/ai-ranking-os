"""Add normalized Research responses.

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "research_responses",
        sa.Column("prompt", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "research_responses",
        sa.Column("raw_response", sa.JSON(), server_default="{}", nullable=False),
    )
    op.add_column(
        "research_responses",
        sa.Column(
            "normalized_response",
            sa.JSON(),
            server_default="{}",
            nullable=False,
        ),
    )
    op.add_column(
        "research_responses",
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "research_responses",
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "research_responses",
        sa.Column("cost", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "research_responses",
        sa.Column("error_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "research_responses",
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "research_responses",
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE research_responses SET "
            "raw_response = raw_payload, "
            "input_tokens = prompt_tokens, "
            "output_tokens = completion_tokens, "
            "finished_at = created_at"
        )
    )


def downgrade() -> None:
    for column in (
        "finished_at",
        "error_message",
        "error_type",
        "cost",
        "output_tokens",
        "input_tokens",
        "normalized_response",
        "raw_response",
        "prompt",
    ):
        op.drop_column("research_responses", column)
