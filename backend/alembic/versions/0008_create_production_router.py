"""Create production LLM Router storage.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "router_models",
        sa.Column("id", sa.String(length=200), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("tier", sa.String(length=30), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("input_cost_per_million", sa.Float(), nullable=False),
        sa.Column("output_cost_per_million", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("quality", sa.Float(), nullable=False),
        sa.Column("availability", sa.Float(), nullable=False),
        sa.Column("context_window", sa.Integer(), nullable=False),
        sa.Column("hallucination_rate", sa.Float(), nullable=False),
        sa.Column("domains", sa.JSON(), nullable=False),
        sa.Column("languages", sa.JSON(), nullable=False),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("provider", "status", "tier"):
        op.create_index(f"ix_router_models_{column}", "router_models", [column])

    op.create_table(
        "router_policies",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("execution_mode", sa.String(length=30), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("required_capabilities", sa.JSON(), nullable=False),
        sa.Column("daily_budget_usd", sa.Float(), nullable=True),
        sa.Column("monthly_budget_usd", sa.Float(), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_router_policies_enabled", "router_policies", ["enabled"])

    op.create_table(
        "router_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.String(length=200), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=False),
        sa.Column("policy_id", sa.String(length=100), nullable=False),
        sa.Column("selected_models", sa.JSON(), nullable=False),
        sa.Column("execution_mode", sa.String(length=30), nullable=False),
        sa.Column("routing_scores", sa.JSON(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("fallback_count", sa.Integer(), nullable=False),
        sa.Column("budget_downgraded", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("correlation_id", "intent", "policy_id", "created_at"):
        op.create_index(f"ix_router_history_{column}", "router_history", [column])

    op.create_table(
        "router_cost_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.String(length=200), nullable=False),
        sa.Column("model_id", sa.String(length=200), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("cost_type", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("correlation_id", "model_id", "provider", "created_at"):
        op.create_index(f"ix_router_cost_logs_{column}", "router_cost_logs", [column])

    op.create_table(
        "router_circuit_breakers",
        sa.Column("model_id", sa.String(length=200), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("model_id"),
    )
    op.create_index(
        "ix_router_circuit_breakers_state",
        "router_circuit_breakers",
        ["state"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_router_circuit_breakers_state",
        table_name="router_circuit_breakers",
    )
    op.drop_table("router_circuit_breakers")
    for column in reversed(("correlation_id", "model_id", "provider", "created_at")):
        op.drop_index(f"ix_router_cost_logs_{column}", table_name="router_cost_logs")
    op.drop_table("router_cost_logs")
    for column in reversed(("correlation_id", "intent", "policy_id", "created_at")):
        op.drop_index(f"ix_router_history_{column}", table_name="router_history")
    op.drop_table("router_history")
    op.drop_index("ix_router_policies_enabled", table_name="router_policies")
    op.drop_table("router_policies")
    for column in reversed(("provider", "status", "tier")):
        op.drop_index(f"ix_router_models_{column}", table_name="router_models")
    op.drop_table("router_models")

