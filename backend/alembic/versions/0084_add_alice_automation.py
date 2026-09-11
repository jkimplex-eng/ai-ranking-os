"""add Alice automated monitoring

Revision ID: 0084
Revises: 0083
"""

import sqlalchemy as sa
from alembic import op

revision = "0084"
down_revision = "0083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alice_automation_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_user_id",
            sa.Integer(),
            sa.ForeignKey("auth_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "template_research_id",
            sa.Integer(),
            sa.ForeignKey("researches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("brand", sa.String(300), nullable=False),
        sa.Column("website_url", sa.Text(), nullable=False),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("region", sa.String(20), nullable=False),
        sa.Column("research_profile", sa.String(40), nullable=False),
        sa.Column("routing_profile", sa.String(40), nullable=False),
        sa.Column("models", sa.JSON(), nullable=False),
        sa.Column("repetitions", sa.Integer(), nullable=False),
        sa.Column("daily_query_limit", sa.Integer(), nullable=False),
        sa.Column("weekly_query_limit", sa.Integer(), nullable=False),
        sa.Column("daily_budget_usd", sa.Float(), nullable=False),
        sa.Column("monthly_budget_usd", sa.Float(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_alice_automation_plans_organization_id", "alice_automation_plans", ["organization_id"]
    )
    op.create_index(
        "ix_alice_automation_due", "alice_automation_plans", ["is_enabled", "next_run_at"]
    )
    op.create_index(
        "ix_alice_automation_org_brand", "alice_automation_plans", ["organization_id", "brand"]
    )

    op.create_table(
        "alice_automation_query_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("alice_automation_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("queries", sa.JSON(), nullable=False),
        sa.Column("source_metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_alice_automation_query_sets_plan_id", "alice_automation_query_sets", ["plan_id"]
    )
    op.create_index(
        "uq_alice_query_set_version",
        "alice_automation_query_sets",
        ["plan_id", "version", "kind"],
        unique=True,
    )

    op.create_table(
        "alice_automation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("alice_automation_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "query_set_id",
            sa.Integer(),
            sa.ForeignKey("alice_automation_query_sets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("run_kind", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("research_id", sa.Integer(), sa.ForeignKey("researches.id", ondelete="SET NULL")),
        sa.Column("task_count", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
        sa.Column("actual_cost_usd", sa.Float()),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_alice_automation_runs_plan_id", "alice_automation_runs", ["plan_id"])
    op.create_index(
        "ix_alice_automation_run_plan_started", "alice_automation_runs", ["plan_id", "started_at"]
    )
    op.create_index(
        "uq_alice_automation_one_running",
        "alice_automation_runs",
        ["plan_id"],
        unique=True,
        postgresql_where=sa.text("status = 'RUNNING'"),
        sqlite_where=sa.text("status = 'RUNNING'"),
    )


def downgrade() -> None:
    op.drop_table("alice_automation_runs")
    op.drop_table("alice_automation_query_sets")
    op.drop_table("alice_automation_plans")
