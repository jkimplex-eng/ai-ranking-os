"""add controlled publication experiment evidence

Revision ID: 0078
Revises: 0077
"""

import sqlalchemy as sa
from alembic import op

revision = "0078"
down_revision = "0077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "publication_learning_experiments",
        sa.Column(
            "design_type",
            sa.String(length=40),
            nullable=False,
            server_default="MATCHED_BEFORE_AFTER",
        ),
    )
    op.add_column(
        "publication_learning_experiments",
        sa.Column("treatment_pairs", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "publication_learning_experiments",
        sa.Column("control_pairs", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "publication_learning_experiments",
        sa.Column("adjusted_metric_deltas", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "publication_learning_experiments",
        sa.Column(
            "effect_method",
            sa.String(length=80),
            nullable=False,
            server_default="RAW_BEFORE_AFTER_V1",
        ),
    )
    op.add_column(
        "publication_influence_estimates",
        sa.Column("controlled_experiments", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "publication_influence_estimates",
        sa.Column(
            "effect_method",
            sa.String(length=80),
            nullable=False,
            server_default="RAW_BEFORE_AFTER_V1",
        ),
    )


def downgrade() -> None:
    op.drop_column("publication_influence_estimates", "effect_method")
    op.drop_column("publication_influence_estimates", "controlled_experiments")
    op.drop_column("publication_learning_experiments", "effect_method")
    op.drop_column("publication_learning_experiments", "adjusted_metric_deltas")
    op.drop_column("publication_learning_experiments", "control_pairs")
    op.drop_column("publication_learning_experiments", "treatment_pairs")
    op.drop_column("publication_learning_experiments", "design_type")
