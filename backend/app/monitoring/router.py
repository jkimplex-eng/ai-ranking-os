from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_db
from backend.app.llm_router.api import router_status
from backend.app.monitoring import service
from backend.app.monitoring.metrics import HTTP_LATENCY, HTTP_REQUESTS
from query_executor.models import QueryExecutionHistory

router = APIRouter(tags=["system-monitoring"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/system/health")
def system_health(db: DbSession) -> dict[str, Any]:
    database = service.database_health(db)
    cache = service.cache_health()
    healthy = database["status"] == "healthy"
    return {
        "status": "healthy" if healthy else "unhealthy",
        "database": database,
        "cache": cache,
    }


@router.get("/system/status")
def system_status(db: DbSession) -> dict[str, Any]:
    return {
        "status": "operational",
        "components": service.component_metrics(db),
        "pipeline": service.pipeline_status(),
        "queue": service.queue_metrics(db),
        "errors": service.error_metrics(db),
    }


@router.get("/system/providers")
def system_providers(db: DbSession) -> dict[str, Any]:
    providers = service.provider_status(db)
    return {"providers": providers, "count": len(providers)}


@router.get("/system/router")
def system_router(db: DbSession) -> dict[str, Any]:
    return router_status(db).model_dump(mode="json")


@router.get("/system/pipeline")
def system_pipeline() -> dict[str, Any]:
    return service.pipeline_status()


@router.get("/system/metrics")
def system_metrics(db: DbSession) -> dict[str, Any]:
    latency = db.execute(
        select(
            func.coalesce(func.avg(QueryExecutionHistory.duration_ms), 0),
            func.coalesce(func.max(QueryExecutionHistory.duration_ms), 0),
        )
    ).one()
    return {
        "components": service.component_metrics(db),
        "queue": service.queue_metrics(db),
        "latency_ms": {"executor_avg": float(latency[0]), "executor_max": int(latency[1])},
        "errors": service.error_metrics(db),
        "costs": service.cost_metrics(db),
    }


@router.get("/system/version")
def system_version() -> dict[str, str]:
    settings = get_settings()
    return {
        "version": settings.app_version,
        "release_channel": settings.release_channel,
    }


@router.get("/system/costs")
def system_costs(db: DbSession) -> dict[str, Any]:
    return service.cost_metrics(db)


@router.get("/system/cache")
def system_cache() -> dict[str, Any]:
    return service.cache_health()


@router.get("/system/build")
def system_build() -> dict[str, str]:
    settings = get_settings()
    return {
        "sha": settings.build_sha,
        "channel": settings.release_channel,
        "python": "3.13",
    }


@router.get("/metrics", include_in_schema=True)
def prometheus_metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


__all__ = ["HTTP_LATENCY", "HTTP_REQUESTS", "router"]

