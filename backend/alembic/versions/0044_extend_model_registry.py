"""extend model registry and add versions

Revision ID: 0044
Revises: 0043
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0044"
down_revision: str | None = "0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = [
        sa.Column("version", sa.String(100), nullable=False, server_default="1.0"),
        sa.Column("release_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tokens_per_second", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_latency", sa.Float(), nullable=False, server_default="0"),
        sa.Column("benchmark_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reasoning", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("multimodal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("embeddings", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("json_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tool_calling", sa.Boolean(), nullable=False, server_default=sa.false()),
    ]
    for column in columns:
        op.add_column("router_models", column)
    op.create_table(
        "router_model_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_id", sa.String(200), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_router_model_versions_model_id", "router_model_versions", ["model_id"])
    op.create_index("ix_router_model_versions_version", "router_model_versions", ["version"])
    op.create_index("ix_router_model_versions_created_at", "router_model_versions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_router_model_versions_created_at", table_name="router_model_versions")
    op.drop_index("ix_router_model_versions_version", table_name="router_model_versions")
    op.drop_index("ix_router_model_versions_model_id", table_name="router_model_versions")
    op.drop_table("router_model_versions")
    for name in (
        "tool_calling", "json_mode", "embeddings", "multimodal", "reasoning",
        "benchmark_score", "average_latency", "tokens_per_second", "release_date", "version",
    ):
        op.drop_column("router_models", name)
