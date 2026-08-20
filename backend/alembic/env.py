from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from ai_visibility import models as ai_visibility_models  # noqa: F401
from alert import models as alert_models  # noqa: F401
from analytics import models as analytics_models  # noqa: F401
from apikeys import models as api_key_models  # noqa: F401
from audit import models as audit_models  # noqa: F401
from authentication import models as authentication_models  # noqa: F401
from backend.app import models  # noqa: F401
from backend.app.config import get_settings
from backend.app.database import Base
from backend.app.llm_router import models as llm_router_models  # noqa: F401
from backend.app.providers import models as provider_models  # noqa: F401
from baseline import models as baseline_models  # noqa: F401
from benchmark import models as benchmark_models  # noqa: F401
from cache import models as cache_models  # noqa: F401
from change_detection import models as change_detection_models  # noqa: F401
from closed_beta import models as closed_beta_models  # noqa: F401
from competitor_intelligence import models as competitor_intelligence_models  # noqa: F401
from decision_center import models as decision_center_models  # noqa: F401
from eis import models as eis_models  # noqa: F401
from entity_extraction import models as entity_extraction_models  # noqa: F401
from entity_linking import models as entity_linking_models  # noqa: F401
from execution_engine import models as execution_engine_models  # noqa: F401
from feedback_center import models as feedback_center_models  # noqa: F401
from frozen_prompts import models as frozen_prompts_models  # noqa: F401
from geo_platforms import models as geo_platforms_models  # noqa: F401
from graph import models as graph_models  # noqa: F401
from hardening import models as hardening_models  # noqa: F401
from influence import models as influence_models  # noqa: F401
from insights import models as insights_models  # noqa: F401
from notification_center import models as notification_center_models  # noqa: F401
from observability import models as observability_models  # noqa: F401
from organization_workspace import models as organization_workspace_models  # noqa: F401
from product import models as product_models  # noqa: F401
from product_analytics import models as product_analytics_models  # noqa: F401
from project_monitoring import models as project_monitoring_models  # noqa: F401
from provider_connections import models as provider_connections_models  # noqa: F401
from publication_learning import models as publication_learning_models  # noqa: F401
from query_executor import models as query_executor_models  # noqa: F401
from query_intent import models as query_intent_models  # noqa: F401
from rate_limit import models as rate_limit_models  # noqa: F401
from rbac import models as rbac_models  # noqa: F401
from recommendation import models as recommendation_models  # noqa: F401
from recommendation.simulation import models as recommendation_simulation_models  # noqa: F401
from recommendation.templates import models as recommendation_template_models  # noqa: F401
from relationship_discovery import models as relationship_discovery_models  # noqa: F401
from report_center import models as report_center_models  # noqa: F401
from report_sharing import models as report_sharing_models  # noqa: F401
from research import models as research_models  # noqa: F401
from research_lab import models as research_lab_models  # noqa: F401
from scheduler import models as scheduler_models  # noqa: F401
from segmentation import models as segmentation_models  # noqa: F401
from trend import models as trend_models  # noqa: F401
from workspace import models as workspace_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
