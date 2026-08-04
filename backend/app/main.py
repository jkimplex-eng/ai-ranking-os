from time import perf_counter

from fastapi import FastAPI, Request

from ai_visibility.router import router as ai_visibility_router
from alert.router import router as alert_router
from analytics.router import router as analytics_router
from apikeys.router import router as api_keys_router
from audit.router import router as audit_router
from authentication.router import router as authentication_router
from backend.app.config import get_settings
from backend.app.llm_router.api import router as llm_router
from backend.app.monitoring.metrics import HTTP_LATENCY, HTTP_REQUESTS
from backend.app.monitoring.router import router as monitoring_router
from backend.app.schemas import HealthResponse, VersionResponse
from baseline.router import router as baseline_router
from benchmark.router import router as benchmark_router
from cache.router import router as cache_router
from decision_center.router import router as decision_center_router
from entity_extraction.router import router as entity_extraction_router
from entity_linking.router import router as entity_linking_router
from execution_engine.router import router as execution_engine_router
from export_engine.router import router as export_router
from graph.router import router as graph_router
from graph_search.router import router as graph_search_router
from hardening.router import router as hardening_router
from influence.router import router as influence_router
from insights.router import router as insights_router
from observability.router import router as observability_router
from query_executor.router import router as query_executor_router
from query_intent.router import router as query_intent_router
from rate_limit.router import router as rate_limit_router
from rbac.router import router as rbac_router
from recommendation.router import router as recommendation_router
from recommendation.simulation.router import router as recommendation_simulation_router
from recommendation.templates.router import router as recommendation_templates_router
from relationship_discovery.router import router as relationship_discovery_router
from research.router import router as research_router
from scheduler.router import router as scheduler_router
from segmentation.router import router as segmentation_router
from trend.router import router as trend_router

settings = get_settings()

app = FastAPI(
    title="AI Ranking OS API",
    description="Core API for the AI Ranking OS platform.",
    version=settings.app_version,
)
app.include_router(decision_center_router)
app.include_router(authentication_router)
app.include_router(rbac_router)
app.include_router(api_keys_router)
app.include_router(audit_router)
app.include_router(observability_router)
app.include_router(cache_router)
app.include_router(rate_limit_router)
app.include_router(hardening_router)
app.include_router(execution_engine_router)
app.include_router(ai_visibility_router)
app.include_router(entity_extraction_router)
app.include_router(query_intent_router)
app.include_router(research_router)
app.include_router(recommendation_router)
app.include_router(recommendation_simulation_router)
app.include_router(recommendation_templates_router)
app.include_router(query_executor_router)
app.include_router(llm_router)
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
    response = await call_next(request)
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    HTTP_REQUESTS.labels(
        method=request.method,
        path=path,
        status=response.status_code,
    ).inc()
    HTTP_LATENCY.labels(method=request.method, path=path).observe(perf_counter() - started)
    return response


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Return process liveness."""

    return HealthResponse(status="ok")


@app.get("/version", response_model=VersionResponse, tags=["system"])
async def version() -> VersionResponse:
    """Return the configured application version."""

    return VersionResponse(version=settings.app_version)
