"""Create AI Visibility Engine history and weight versions.

Revision ID: 0004
Revises: 0003
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_WEIGHTS = {
    "mention_frequency": 0.20,
    "recommendation_position": 0.15,
    "citation_count": 0.10,
    "citation_authority": 0.15,
    "cross_model_presence": 0.15,
    "consistency": 0.10,
    "entity_confidence": 0.10,
    "freshness": 0.05,
}


def upgrade() -> None:
    op.create_table(
        "visibility_weight_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version"),
    )
    op.create_index(
        "ix_visibility_weight_sets_is_active",
        "visibility_weight_sets",
        ["is_active"],
    )
    # Escape JSON colons so SQLAlchemy text does not interpret numeric values as
    # bind parameter names while Alembic renders an offline PostgreSQL script.
    serialized_weights = json.dumps(DEFAULT_WEIGHTS, separators=(",", ":")).replace(
        ":",
        r"\:",
    )
    op.execute(
        sa.text(
            "INSERT INTO visibility_weight_sets (version, weights, is_active) "
            f"VALUES ('1.0', '{serialized_weights}', true)"
        )
    )

    op.create_table(
        "visibility_calculations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_id", sa.String(length=200), nullable=False),
        sa.Column("entity", sa.String(length=300), nullable=False),
        sa.Column("visibility_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("weight_version", sa.String(length=50), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_visibility_calculations_calculated_at",
        "visibility_calculations",
        ["calculated_at"],
    )
    op.create_index(
        "ix_visibility_calculations_entity_id",
        "visibility_calculations",
        ["entity_id"],
    )
    op.create_index(
        "ix_visibility_calculations_weight_version",
        "visibility_calculations",
        ["weight_version"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_visibility_calculations_weight_version",
        table_name="visibility_calculations",
    )
    op.drop_index(
        "ix_visibility_calculations_entity_id",
        table_name="visibility_calculations",
    )
    op.drop_index(
        "ix_visibility_calculations_calculated_at",
        table_name="visibility_calculations",
    )
    op.drop_table("visibility_calculations")
    op.drop_index(
        "ix_visibility_weight_sets_is_active",
        table_name="visibility_weight_sets",
    )
    op.drop_table("visibility_weight_sets")
