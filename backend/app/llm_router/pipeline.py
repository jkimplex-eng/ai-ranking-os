from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.llm_router.config_loader import policy_config, provider_config, router_config
from backend.app.llm_router.cost_optimizer import optimize_for_budget
from backend.app.llm_router.ensemble import build_ensemble_plan
from backend.app.llm_router.execution_plan import build_execution_plan
from backend.app.llm_router.fallback import build_fallback_plan
from backend.app.llm_router.metrics import (
    ROUTER_COST,
    ROUTER_FALLBACKS,
    ROUTER_LATENCY,
    ROUTER_REQUESTS,
    ROUTER_SCORE,
    ROUTER_SELECTED,
)
from backend.app.llm_router.models import RouterCostLog, RouterHistory
from backend.app.llm_router.parallel import build_parallel_plan
from backend.app.llm_router.policy import resolve_policy
from backend.app.llm_router.registry import ModelRepository, ensure_seeded
from backend.app.llm_router.schemas import (
    ModelRead,
    PolicyRead,
    RouteRequest,
    RouteResponse,
    ScoreBreakdown,
)
from backend.app.llm_router.scoring import score_model
from backend.app.llm_router.selector import select_models
from query_executor.schemas import ExecutionMode, ExecutionPlan
from query_intent.pipeline import run_pipeline as classify_intent
from query_intent.schemas import IntentInput, IntentType


class RoutingError(RuntimeError):
    """No valid route could be produced."""


def _build_plan(
    request: RouteRequest,
    correlation_id: str,
    models: list[ModelRead],
    mode: ExecutionMode,
) -> ExecutionPlan:
    builders = {
        ExecutionMode.PARALLEL: build_parallel_plan,
        ExecutionMode.ENSEMBLE: build_ensemble_plan,
        ExecutionMode.FALLBACK: build_fallback_plan,
    }
    if mode == ExecutionMode.CONSENSUS:
        return build_execution_plan(
            request,
            correlation_id=correlation_id,
            models=models,
            mode=ExecutionMode.CONSENSUS,
        )
    builder = builders.get(mode)
    if builder:
        return builder(request, correlation_id, models)
    return build_execution_plan(
        request,
        correlation_id=correlation_id,
        models=models[:1],
        mode=ExecutionMode.SINGLE,
    )


def _response(
    request: RouteRequest,
    *,
    correlation_id: str,
    intent: IntentType,
    policy: PolicyRead,
    models: list[ModelRead],
    scores: list[ScoreBreakdown],
    budget_downgraded: bool,
    latency_ms: float,
) -> RouteResponse:
    selected_count = min(policy.top_k, len(models))
    selected_models = models[:selected_count]
    selected_scores = scores[:selected_count]
    mode = policy.execution_mode
    if mode in {ExecutionMode.ENSEMBLE, ExecutionMode.CONSENSUS} and selected_count < 2:
        mode = ExecutionMode.SINGLE
    fallback_count = max(0, selected_count - 1) if mode == ExecutionMode.FALLBACK else 0
    plan = _build_plan(request, correlation_id, selected_models, mode)
    return RouteResponse(
        correlation_id=correlation_id,
        intent=intent,
        policy_id=policy.id,
        selected_models=[model.id for model in selected_models],
        scores=selected_scores,
        plan=plan,
        estimated_cost_usd=round(
            sum(score.estimated_cost_usd for score in selected_scores),
            8,
        ),
        budget_downgraded=budget_downgraded,
        fallback_count=fallback_count,
        router_latency_ms=round(latency_ms, 3),
    )


def route(db: Session, request: RouteRequest) -> RouteResponse:
    started = perf_counter()
    ensure_seeded(db)
    correlation_id = request.correlation_id or str(uuid4())
    intent = request.intent or classify_intent(
        IntentInput(request_id=correlation_id, query=request.query)
    ).primary_intent
    if request.language is None:
        request.language = classify_intent(
            IntentInput(request_id=correlation_id, query=request.query)
        ).language.code
    policy = resolve_policy(db, request)
    models, scores = select_models(
        db,
        ModelRepository(db).all_active(),
        request,
        intent,
        policy.weights,
        policy.required_capabilities,
    )
    if not models:
        ROUTER_REQUESTS.labels(policy=policy.id, status="error").inc()
        raise RoutingError("No available model satisfies routing constraints")
    models, scores, downgraded = optimize_for_budget(db, models, scores, policy)
    latency_ms = (perf_counter() - started) * 1000
    response = _response(
        request,
        correlation_id=correlation_id,
        intent=intent,
        policy=policy,
        models=models,
        scores=scores,
        budget_downgraded=downgraded,
        latency_ms=latency_ms,
    )
    now = datetime.now(UTC)
    db.add(
        RouterHistory(
            correlation_id=correlation_id,
            query=request.query,
            intent=intent,
            policy_id=policy.id,
            selected_models=response.selected_models,
            execution_mode=response.plan.mode,
            routing_scores={
                score.model_id: score.model_dump(mode="json")
                for score in response.scores
            },
            estimated_cost_usd=response.estimated_cost_usd,
            latency_ms=response.router_latency_ms,
            fallback_count=response.fallback_count,
            budget_downgraded=response.budget_downgraded,
            created_at=now,
        )
    )
    selected_by_id = {model.id: model for model in models}
    for score in response.scores:
        model = selected_by_id[score.model_id]
        db.add(
            RouterCostLog(
                correlation_id=correlation_id,
                model_id=model.id,
                provider=model.provider,
                input_tokens=request.context_tokens,
                output_tokens=request.max_output_tokens,
                cost_usd=score.estimated_cost_usd,
                cost_type="ESTIMATED",
                created_at=now,
            )
        )
        ROUTER_SELECTED.labels(model=model.id, provider=model.provider).inc()
        ROUTER_COST.labels(model=model.id, provider=model.provider).inc(
            score.estimated_cost_usd
        )
        ROUTER_SCORE.labels(model=model.id).observe(score.total)
    db.commit()
    ROUTER_REQUESTS.labels(policy=policy.id, status="success").inc()
    ROUTER_LATENCY.labels(policy=policy.id).observe(latency_ms / 1000)
    if response.fallback_count:
        ROUTER_FALLBACKS.labels(policy=policy.id).inc(response.fallback_count)
    return response


def route_from_config(request: RouteRequest) -> RouteResponse:
    """Production config-backed routing for offline validation and bootstrap."""

    started = perf_counter()
    now = datetime.now(UTC)
    models = []
    for raw in provider_config().get("models", []):
        models.append(
            ModelRead(
                id=raw["id"],
                provider=raw["provider"],
                display_name=raw["display_name"],
                status=raw["status"],
                tier=raw["tier"],
                capabilities=raw["capabilities"],
                pricing=raw["pricing"],
                latency_ms=raw["latency_ms"],
                quality=raw["quality"],
                availability=raw["availability"],
                context_window=raw["context_window"],
                hallucination_rate=raw["hallucination_rate"],
                domains=raw["domains"],
                languages=raw["languages"],
                region=raw.get("region", "GLOBAL"),
                success_probability=raw.get("success_probability", 0.95),
                created_at=now,
                updated_at=now,
            )
        )
    policy_id = request.policy_id or router_config()["defaults"]["policy_id"]
    raw_policy = next(
        item for item in policy_config()["policies"] if item["id"] == policy_id
    )
    budgets = router_config().get("budgets", {})
    policy = PolicyRead(
        id=raw_policy["id"],
        name=raw_policy["name"],
        enabled=True,
        execution_mode=raw_policy["execution_mode"],
        top_k=raw_policy["top_k"],
        weights=raw_policy["weights"],
        required_capabilities=raw_policy.get("required_capabilities", []),
        daily_budget_usd=budgets.get("daily_usd"),
        monthly_budget_usd=budgets.get("monthly_usd"),
        settings={},
        updated_at=now,
    )
    correlation_id = request.correlation_id or str(uuid4())
    intent_result = classify_intent(
        IntentInput(request_id=correlation_id, query=request.query)
    )
    intent = request.intent or intent_result.primary_intent
    request.language = request.language or intent_result.language.code
    scored = [
        score_model(model, request, intent, policy.weights)
        for model in models
        if model.status == "ACTIVE"
        and model.context_window >= request.context_tokens
        and set(policy.required_capabilities).issubset(model.capabilities)
    ]
    scored.sort(key=lambda item: (-item.total, item.estimated_cost_usd))
    by_id = {model.id: model for model in models}
    ordered = [by_id[score.model_id] for score in scored]
    return _response(
        request,
        correlation_id=correlation_id,
        intent=intent,
        policy=policy,
        models=ordered,
        scores=scored,
        budget_downgraded=False,
        latency_ms=(perf_counter() - started) * 1000,
    )
