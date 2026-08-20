import logging
import os
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter, time

from fastapi import FastAPI, Request
from sqlalchemy import inspect

from ai_visibility.router import router as ai_visibility_router
from alert.router import router as alert_router
from analytics.router import router as analytics_router
from apikeys.router import router as api_keys_router
from audit.router import router as audit_router
from authentication.middleware import ProductionAuthenticationMiddleware
from authentication.router import router as authentication_router
from backend.app.config import get_settings
from backend.app.database import SessionLocal, engine
from backend.app.llm_router.api import router as llm_router
from backend.app.logging import bind_request, configure_logging, user_id_var
from backend.app.monitoring.metrics import HTTP_LATENCY, HTTP_REQUESTS
from backend.app.monitoring.router import router as monitoring_router
from backend.app.providers.api import router as providers_router
from backend.app.schemas import HealthResponse, VersionResponse
from baseline.router import router as baseline_router
from benchmark.router import router as benchmark_router
from cache.router import router as cache_router
from change_detection.router import router as change_detection_router
from closed_beta.router import router as closed_beta_router
from competitor_intelligence.router import router as competitor_intelligence_router
from cost_analytics.router import router as cost_analytics_router
from decision_center.router import router as decision_center_router
from eis.router import router as eis_router
from entity_extraction.router import router as entity_extraction_router
from entity_linking.router import router as entity_linking_router
from execution_engine.router import router as execution_engine_router
from export_engine.router import router as export_router
from feedback_center.router import router as feedback_center_router
from frozen_prompts.router import router as frozen_prompts_router
from geo_platforms.router import router as geo_platforms_router
from graph.router import router as graph_router
from graph_search.router import router as graph_search_router
from hardening.router import router as hardening_router
from hardening.validation import validate_startup
from influence.router import router as influence_router
from insights.router import router as insights_router
from model_benchmark.router import router as model_benchmark_router
from model_evaluation.router import router as model_evaluation_router
from notification_center.router import router as notification_center_router
from observability.router import router as observability_router
from organization_workspace.router import router as organization_workspace_router
from product.router import router as product_router
from product_analytics.instrumentation import request_event
from product_analytics.repository import ProductAnalyticsRepository
from product_analytics.router import router as product_analytics_router
from product_analytics.service import ProductAnalyticsService
from project_monitoring.router import router as project_monitoring_router
from provider_connections.crypto import SecretCipher
from provider_connections.repository import ProviderConnectionRepository
from provider_connections.router import router as provider_connections_router
from provider_connections.service import hydrate_provider_credentials
from provider_discovery.router import router as provider_discovery_router
from provider_recommendation.router import router as provider_recommendation_router
from provider_registry.router import router as provider_registry_router
from publication_learning.router import router as publication_learning_router
from query_executor.router import router as query_executor_router
from query_intent.router import router as query_intent_router
from rate_limit.router import router as rate_limit_router
from rbac.router import router as rbac_router
from recommendation.router import router as recommendation_router
from recommendation.simulation.router import router as recommendation_simulation_router
from recommendation.templates.router import router as recommendation_templates_router
from relationship_discovery.router import router as relationship_discovery_router
from report_center.router import router as report_center_router
from report_sharing.router import router as report_sharing_router
from research.router import router as research_router
from research_lab.router import router as research_lab_router
from scheduler.router import router as scheduler_router
from segmentation.router import router as segmentation_router
from trend.router import router as trend_router
from workspace.router import router as workspace_router

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("ai_ranking_os.http")
started_at = time()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    errors = validate_startup(settings)
    if errors:
        raise RuntimeError("Startup validation failed: " + "; ".join(errors))
    with SessionLocal() as db:
        if inspect(db.get_bind()).has_table("provider_connections"):
            hydrate_provider_credentials(
                ProviderConnectionRepository(db),
                SecretCipher(settings.provider_secret_key or settings.auth_jwt_secret),
            )
        else:
            logger.warning(
                "provider_credentials_hydration_skipped",
                extra={"reason": "table_missing"},
            )
    if os.getenv("PROVIDER_CATALOG_URL"):
        from provider_discovery.service import ProviderDiscoveryService

        with SessionLocal() as db:
            ProviderDiscoveryService(db).sync()
    yield
    engine.dispose()


app = FastAPI(
    title="AI Ranking OS API",
    description="Core API for the AI Ranking OS platform.",
    version=settings.app_version,
    lifespan=lifespan,
)
app.add_middleware(ProductionAuthenticationMiddleware, settings=settings)
app.include_router(decision_center_router)
app.include_router(authentication_router)
app.include_router(workspace_router)
app.include_router(report_center_router)
app.include_router(report_sharing_router)
app.include_router(rbac_router)
app.include_router(api_keys_router)
app.include_router(audit_router)
app.include_router(observability_router)
app.include_router(organization_workspace_router)
app.include_router(cache_router)
app.include_router(change_detection_router)
app.include_router(closed_beta_router)
app.include_router(competitor_intelligence_router)
app.include_router(rate_limit_router)
app.include_router(hardening_router)
app.include_router(execution_engine_router)
app.include_router(feedback_center_router)
app.include_router(ai_visibility_router)
app.include_router(entity_extraction_router)
app.include_router(query_intent_router)
app.include_router(product_router)
app.include_router(product_analytics_router)
app.include_router(project_monitoring_router)
app.include_router(research_lab_router)
app.include_router(publication_learning_router)
app.include_router(geo_platforms_router)
app.include_router(frozen_prompts_router)
app.include_router(eis_router)
app.include_router(research_router)
app.include_router(recommendation_router)
app.include_router(recommendation_simulation_router)
app.include_router(recommendation_templates_router)
app.include_router(query_executor_router)
app.include_router(llm_router)
app.include_router(providers_router)
app.include_router(provider_connections_router)
app.include_router(model_benchmark_router)
app.include_router(model_evaluation_router)
app.include_router(notification_center_router)
app.include_router(cost_analytics_router)
app.include_router(provider_discovery_router)
app.include_router(provider_recommendation_router)
app.include_router(provider_registry_router)
app.include_router(monitoring_router)
app.include_router(trend_router)
app.include_router(alert_router)
app.include_router(scheduler_router)
app.include_router(baseline_router)
app.include_router(analytics_router)
app.include_router(segmentation_router)
app.include_router(benchmark_router)
app.include_router(export_router)
app.include_router(insights_router)
app.include_router(graph_search_router)
app.include_router(influence_router)
app.include_router(graph_router)
app.include_router(entity_linking_router)
app.include_router(relationship_discovery_router)


@app.middleware("http")
async def observe_http(request: Request, call_next):
    started = perf_counter()
    request_id = bind_request(request)
    try:
        response = await call_next(request)
    except Exception:
        try:
            with SessionLocal() as analytics_db:
                ProductAnalyticsService(ProductAnalyticsRepository(analytics_db)).record(
                    request_event(
                        method=request.method,
                        route=request.url.path,
                        status=500,
                        latency_ms=(perf_counter() - started) * 1000,
                        user_id=None,
                        session_id=None,
                        ip_address=request.client.host if request.client else None,
                        ip_salt=settings.auth_jwt_secret,
                        user_agent=request.headers.get("user-agent"),
                    )
                )
        except Exception:
            logger.exception("product_analytics_error_record_failed")
        logger.exception(
            "request_failed",
            extra={"latency_ms": round((perf_counter() - started) * 1000, 2)},
        )
        raise
    principal = getattr(request.state, "principal", None)
    if principal is not None:
        user_id_var.set(str(getattr(principal, "user_id", getattr(principal, "id", "-"))))
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    HTTP_REQUESTS.labels(
        method=request.method,
        path=path,
        status=response.status_code,
    ).inc()
    HTTP_LATENCY.labels(method=request.method, path=path).observe(perf_counter() - started)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed method=%s path=%s status=%s",
        request.method,
        path,
        response.status_code,
        extra={"latency_ms": round((perf_counter() - started) * 1000, 2)},
    )
    if not request.url.path.startswith("/product-analytics"):
        try:
            principal_user_id = getattr(
                principal, "user_id", getattr(principal, "id", None)
            )
            with SessionLocal() as analytics_db:
                ProductAnalyticsService(ProductAnalyticsRepository(analytics_db)).record(
                    request_event(
                        method=request.method,
                        route=path,
                        status=response.status_code,
                        latency_ms=(perf_counter() - started) * 1000,
                        user_id=int(principal_user_id) if principal_user_id else None,
                        session_id=str(getattr(principal, "session_id", "")) or None,
                        ip_address=request.client.host if request.client else None,
                        ip_salt=settings.auth_jwt_secret,
                        user_agent=request.headers.get("user-agent"),
                    )
                )
        except Exception:
            logger.exception("product_analytics_record_failed")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path not in {"/docs", "/redoc", "/openapi.json"}:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if settings.app_env.lower() in {"production", "prod"}:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Return process liveness."""

    return HealthResponse(status="ok")


@app.get("/live", tags=["system"])
async def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/ready", tags=["system"])
async def ready() -> dict[str, object]:
    from redis import Redis
    from sqlalchemy import text

    database = "available"
    redis = "available"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        database = "unavailable"
    try:
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=0.5, socket_timeout=0.5)
        client.ping()
        client.close()
    except Exception:
        redis = "degraded"
    return {
        "status": "ready" if database == "available" else "not_ready",
        "database": database,
        "redis": redis,
        "uptime_seconds": round(time() - started_at, 3),
    }


@app.get("/system/resources", tags=["system-monitoring"])
async def resources() -> dict[str, object]:
    usage = shutil.disk_usage("/")
    return {
        "disk": {"total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free},
        "memory": {"source": "container_limits", "note": "exported by platform runtime"},
    }


@app.get("/version", response_model=VersionResponse, tags=["system"])
async def version() -> VersionResponse:
    """Return the configured application version."""

    return VersionResponse(version=settings.app_version)
