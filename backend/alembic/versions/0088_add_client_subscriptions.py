"""add client subscription administration

Revision ID: 0089_client_subscriptions
Revises: 0088
"""

import sqlalchemy as sa
from alembic import op

revision = "0089_client_subscriptions"
down_revision = "0088"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "beta_user_profiles",
        sa.Column("plan_code", sa.String(40), nullable=False, server_default="trial"),
    )
    op.add_column(
        "beta_user_profiles",
        sa.Column("subscription_status", sa.String(20), nullable=False, server_default="NONE"),
    )
    op.add_column(
        "beta_user_profiles", sa.Column("subscription_started_at", sa.DateTime(timezone=True))
    )
    op.add_column(
        "beta_user_profiles", sa.Column("subscription_ends_at", sa.DateTime(timezone=True))
    )
    op.add_column("beta_user_profiles", sa.Column("payment_provider", sa.String(40)))
    op.add_column("beta_user_profiles", sa.Column("external_customer_id", sa.String(200)))
    op.add_column("beta_user_profiles", sa.Column("external_subscription_id", sa.String(200)))
    op.create_index(
        "ix_beta_user_profiles_subscription_status", "beta_user_profiles", ["subscription_status"]
    )
    op.create_index("ix_beta_user_profiles_plan_code", "beta_user_profiles", ["plan_code"])


def downgrade() -> None:
    op.drop_index("ix_beta_user_profiles_plan_code", table_name="beta_user_profiles")
    op.drop_index("ix_beta_user_profiles_subscription_status", table_name="beta_user_profiles")
    for name in (
        "external_subscription_id",
        "external_customer_id",
        "payment_provider",
        "subscription_ends_at",
        "subscription_started_at",
        "subscription_status",
        "plan_code",
    ):
        op.drop_column("beta_user_profiles", name)
