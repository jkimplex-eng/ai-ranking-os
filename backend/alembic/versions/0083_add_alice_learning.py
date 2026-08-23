"""add Alice recommendation learning

Revision ID: 0083
Revises: 0082
"""

import sqlalchemy as sa
from alembic import op

revision = "0083"
down_revision = "0082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alice_learning_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "research_id",
            sa.Integer(),
            sa.ForeignKey("researches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "response_id",
            sa.Integer(),
            sa.ForeignKey("research_responses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("brand", sa.String(300), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("region", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("mentioned", sa.Boolean(), nullable=False),
        sa.Column("recommended", sa.Boolean(), nullable=False),
        sa.Column("cited", sa.Boolean(), nullable=False),
        sa.Column("recommendation_rank", sa.Integer()),
        sa.Column("source_domains", sa.JSON(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("feature_evidence", sa.JSON(), nullable=False),
        sa.Column("evidence_status", sa.String(30), nullable=False),
        sa.Column("feature_version", sa.String(20), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_alice_learning_observations_organization_id",
        "alice_learning_observations",
        ["organization_id"],
    )
    op.create_index(
        "ix_alice_learning_observations_research_id",
        "alice_learning_observations",
        ["research_id"],
    )
    op.create_index(
        "uq_alice_learning_response_version",
        "alice_learning_observations",
        ["response_id", "feature_version"],
        unique=True,
    )
    op.create_index(
        "ix_alice_learning_org_category_observed",
        "alice_learning_observations",
        ["organization_id", "category", "observed_at"],
    )

    op.create_table(
        "alice_learning_models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("region", sa.String(20), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("model_type", sa.String(80), nullable=False),
        sa.Column("intercept", sa.Float(), nullable=False),
        sa.Column("coefficients", sa.JSON(), nullable=False),
        sa.Column("feature_statistics", sa.JSON(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("positive_samples", sa.Integer(), nullable=False),
        sa.Column("negative_samples", sa.Integer(), nullable=False),
        sa.Column("validation", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("algorithm_version", sa.String(20), nullable=False),
        sa.Column(
            "trained_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_alice_learning_models_organization_id",
        "alice_learning_models",
        ["organization_id"],
    )
    op.create_index(
        "ix_alice_learning_model_dimension",
        "alice_learning_models",
        ["organization_id", "category", "language", "region", "trained_at"],
    )

    op.create_table(
        "alice_learning_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "model_id",
            sa.Integer(),
            sa.ForeignKey("alice_learning_models.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("brand", sa.String(300), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("counterfactuals", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("evidence_status", sa.String(30), nullable=False),
        sa.Column("algorithm_version", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_alice_learning_predictions_organization_id",
        "alice_learning_predictions",
        ["organization_id"],
    )
    op.create_index(
        "ix_alice_learning_prediction_org_created",
        "alice_learning_predictions",
        ["organization_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_alice_learning_prediction_org_created",
        table_name="alice_learning_predictions",
    )
    op.drop_index(
        "ix_alice_learning_predictions_organization_id",
        table_name="alice_learning_predictions",
    )
    op.drop_table("alice_learning_predictions")
    op.drop_index("ix_alice_learning_model_dimension", table_name="alice_learning_models")
    op.drop_index("ix_alice_learning_models_organization_id", table_name="alice_learning_models")
    op.drop_table("alice_learning_models")
    op.drop_index(
        "ix_alice_learning_org_category_observed",
        table_name="alice_learning_observations",
    )
    op.drop_index(
        "uq_alice_learning_response_version",
        table_name="alice_learning_observations",
    )
    op.drop_index(
        "ix_alice_learning_observations_research_id",
        table_name="alice_learning_observations",
    )
    op.drop_index(
        "ix_alice_learning_observations_organization_id",
        table_name="alice_learning_observations",
    )
    op.drop_table("alice_learning_observations")
