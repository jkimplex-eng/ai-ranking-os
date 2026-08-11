import json
from pathlib import Path
from typing import Any

from redis import Redis
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ai_visibility.models import VisibilityCalculation
from backend.app.config import get_settings
from backend.app.llm_router.cost_optimizer import current_costs
from backend.app.llm_router.models import (
    CircuitBreakerRecord,
    RegisteredModel,
    RouterCostLog,
    RouterHistory,
)
from backend.app.llm_router.registry import ensure_seeded
from backend.app.monitoring.metrics import (
    COMPONENT_RECORDS,
    PIPELINE_STATUS,
    QUEUE_DEPTH,
)
from backend.app.providers.health import provider_health
from backend.app.providers.models import ProviderUsageRecord
from decision_center.models import Task, TaskStatus
from entity_extraction.models import EntityExtractionRun
from execution_engine.models import Execution
from query_executor.models import QueryExecutionHistory, QueryProviderMetric
from query_intent.models import IntentClassificationRun

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VALIDATION_REPORT = PROJECT_ROOT / "validation_reports" / "pipeline-validation.json"


def database_health(db: Session) -> dict[str, Any]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        return {"status": "unhealthy", "error": str(error)}
    return {"status": "healthy"}


def cache_health() -> dict[str, Any]:
    settings = get_settings()
    try:
        client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=0.1,
            socket_timeout=0.1,
        )
        available = bool(client.ping())
        client.close()
    except Exception as error:
        return {
            "status": "degraded",
            "available": False,
            "error": type(error).__name__,
        }
    return {"status": "healthy", "available": available}


def pipeline_status() -> dict[str, Any]:
    if not VALIDATION_REPORT.exists():
        PIPELINE_STATUS.set(0)
        return {"status": "unknown", "report": None}
    report = json.loads(VALIDATION_REPORT.read_text(encoding="utf-8"))
    passed = report.get("status") == "PASS"
    PIPELINE_STATUS.set(1 if passed else 0)
    return {
        "status": "healthy" if passed else "unhealthy",
        "validation": report.get("status"),
        "checks": report.get("coverage", {}).get("checks", {}),
        "generated_at": report.get("generated_at"),
    }


def component_metrics(db: Session) -> dict[str, int]:
    models = {
        "router": RouterHistory,
        "executor": QueryExecutionHistory,
        "execution_engine": Execution,
        "visibility": VisibilityCalculation,
        "entity_extraction": EntityExtractionRun,
        "intent": IntentClassificationRun,
    }
    values = {
        name: int(db.scalar(select(func.count()).select_from(model)) or 0)
        for name, model in models.items()
    }
    for name, value in values.items():
        COMPONENT_RECORDS.labels(component=name).set(value)
    return values


def queue_metrics(db: Session) -> dict[str, int]:
    ready = int(
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(Task.status == TaskStatus.READY)
        )
        or 0
    )
    QUEUE_DEPTH.set(ready)
    return {"ready": ready}


def provider_status(db: Session) -> list[dict[str, Any]]:
    ensure_seeded(db)
    circuits = {
        row.model_id: row.state
        for row in db.scalars(select(CircuitBreakerRecord))
    }
    configured = {item["provider"]: item for item in provider_health()}
    return [
        {
            "model_id": model.id,
            "provider": model.provider,
            "status": model.status,
            "availability": model.availability,
            "latency_ms": model.latency_ms,
            "region": model.region,
            "success_probability": model.success_probability,
            "circuit_state": circuits.get(model.id, "CLOSED"),
            "interface": configured.get(
                model.provider,
                {"status": "unknown", "mock": False, "available": False},
            ),
        }
        for model in db.scalars(select(RegisteredModel).order_by(RegisteredModel.id))
    ]


def cost_metrics(db: Session) -> dict[str, Any]:
    daily, monthly = current_costs(db)
    tokens = db.execute(
        select(
            func.coalesce(func.sum(RouterCostLog.input_tokens), 0),
            func.coalesce(func.sum(RouterCostLog.output_tokens), 0),
        )
    ).one()
    actual_spend = db.execute(
        select(
            ProviderUsageRecord.provider,
            ProviderUsageRecord.currency,
            func.coalesce(func.sum(ProviderUsageRecord.estimated_cost), 0),
        ).group_by(ProviderUsageRecord.provider, ProviderUsageRecord.currency)
    ).all()
    actual_tokens = db.execute(
        select(
            func.coalesce(func.sum(ProviderUsageRecord.prompt_tokens), 0),
            func.coalesce(func.sum(ProviderUsageRecord.completion_tokens), 0),
        )
    ).one()
    return {
        "daily_usd": round(daily, 8),
        "monthly_usd": round(monthly, 8),
        "input_tokens": int(tokens[0]),
        "output_tokens": int(tokens[1]),
        "actual_prompt_tokens": int(actual_tokens[0]),
        "actual_completion_tokens": int(actual_tokens[1]),
        "provider_spend": [
            {
                "provider": provider,
                "currency": currency,
                "amount": round(float(amount), 8),
            }
            for provider, currency, amount in actual_spend
        ],
    }


def error_metrics(db: Session) -> dict[str, int]:
    router_errors = int(
        db.scalar(
            select(func.count())
            .select_from(RouterHistory)
            .where(RouterHistory.error.is_not(None))
        )
        or 0
    )
    provider_failures = int(
        db.scalar(
            select(func.count())
            .select_from(QueryProviderMetric)
            .where(QueryProviderMetric.failure.is_not(None))
        )
        or 0
    )
    return {"router": router_errors, "providers": provider_failures}
