"""Add deterministic Recommendation simulations.

Revision ID: 0019
Revises: 0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recommendation_simulations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "recommendation_id",
            sa.Integer(),
            sa.ForeignKey("recommendations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("current_visibility", sa.Float(), nullable=False),
        sa.Column("predicted_visibility", sa.Float(), nullable=False),
        sa.Column("predicted_delta", sa.Float(), nullable=False),
        sa.Column("confidence_min", sa.Float(), nullable=False),
        sa.Column("confidence_expected", sa.Float(), nullable=False),
        sa.Column("confidence_max", sa.Float(), nullable=False),
        sa.Column("estimated_duration_days", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "current_visibility >= 0 AND current_visibility <= 100",
            name="ck_recommendation_simulations_current_visibility",
        ),
        sa.CheckConstraint(
            "predicted_visibility >= 0 AND predicted_visibility <= 100",
            name="ck_recommendation_simulations_predicted_visibility",
        ),
        sa.CheckConstraint(
            "confidence_min <= confidence_expected "
            "AND confidence_expected <= confidence_max",
            name="ck_recommendation_simulations_confidence_order",
        ),
        sa.CheckConstraint(
            "estimated_duration_days > 0",
            name="ck_recommendation_simulations_duration",
        ),
    )
    op.create_index(
        "ix_recommendation_simulations_recommendation_created",
        "recommendation_simulations",
        ["recommendation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_recommendation_simulations_recommendation_created",
        table_name="recommendation_simulations",
    )
    op.drop_table("recommendation_simulations")
