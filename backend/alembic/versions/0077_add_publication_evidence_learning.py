"""add reproducible publication evidence learning

Revision ID: 0077
Revises: 0076
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0077"
down_revision: str | None = "0076"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    experiment_columns = (
        sa.Column("evidence_level", sa.String(20), nullable=False, server_default="HYPOTHESIS"),
        sa.Column("baseline_sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("followup_sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matched_pairs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_responses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "confidence_method",
            sa.String(80),
            nullable=False,
            server_default="MATCHED_RESPONSE_COVERAGE_V1",
        ),
        sa.Column("evidence_matrix", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("limitations", sa.JSON(), nullable=False, server_default="[]"),
    )
    for column in experiment_columns:
        op.add_column("publication_learning_experiments", column)

    estimate_columns = (
        sa.Column("evidence_level", sa.String(20), nullable=False, server_default="OBSERVATION"),
        sa.Column("positive_experiments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("negative_experiments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("neutral_experiments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_observed_at", sa.DateTime(timezone=True)),
        sa.Column("limitations", sa.JSON(), nullable=False, server_default="[]"),
    )
    for column in estimate_columns:
        op.add_column("publication_influence_estimates", column)


def downgrade() -> None:
    for name in (
        "limitations",
        "last_observed_at",
        "neutral_experiments",
        "negative_experiments",
        "positive_experiments",
        "evidence_level",
    ):
        op.drop_column("publication_influence_estimates", name)
    for name in (
        "limitations",
        "evidence_matrix",
        "confidence_method",
        "confidence_score",
        "failed_responses",
        "matched_pairs",
        "followup_sample_size",
        "baseline_sample_size",
        "evidence_level",
    ):
        op.drop_column("publication_learning_experiments", name)
