from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.llm_router.automatic_failover import order_failover_models
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
from backend.app.llm_router.mode import (
    RoutingMode,
    configured_hybrid_order,
    configured_mode,
)
from backend.app.llm_router.models import RouterCostLog, RouterHistory
from backend.app.llm_router.parallel import build_parallel_plan
from backend.app.llm_router.policy import profile_policy, resolve_policy, strategy_for_task
from backend.app.llm_router.ports import ModelEvaluationPort, ProviderReadinessPort
from backend.app.llm_router.registry import ModelRepository, ensure_seeded
from backend.app.llm_router.schemas import (
    ModelRead,
    PolicyRead,
    RouteRequest,
    RouteResponse,
    RouterStrategy,
    ScoreBreakdown,
)
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
    if mode == ExecutionMode.FALLBACK:
        selected_models, selected_scores = order_failover_models(selected_models, selected_scores)
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
        strategy=request.strategy or policy.strategy,
        routing_mode=request.routing_mode or configured_mode(),
        hybrid_order=request.hybrid_order or configured_hybrid_order(),
    )


def route(
    db: Session,
    request: RouteRequest,
    *,
    readiness: ProviderReadinessPort,
    evaluation: ModelEvaluationPort,
) -> RouteResponse:
    started = perf_counter()
    ensure_seeded(db)
    correlation_id = request.correlation_id or str(uuid4())
    intent = (
        request.intent
        or classify_intent(
            IntentInput(request_id=correlation_id, query=request.query)
        ).primary_intent
    )
    if request.language is None:
        request.language = classify_intent(
            IntentInput(request_id=correlation_id, query=request.query)
        ).language.code
    policy = resolve_policy(db, request)
    request.routing_mode = request.routing_mode or configured_mode()
    request.hybrid_order = request.hybrid_order or configured_hybrid_order()
    if request.routing_mode == RoutingMode.LOCAL:
        request.strategy = RouterStrategy.LOCAL_ONLY
    _, profile_strategy = profile_policy(request.profile)
    request.strategy = (
        request.strategy
        or strategy_for_task(request.task_type)
        or (policy.strategy if request.policy_id else profile_strategy)
    )
    models, scores = select_models(
        db,
        ModelRepository(db).all_active(),
        request,
        intent,
        policy.weights,
        policy.required_capabilities,
        readiness,
        evaluation,
    )
    if not models:
        ROUTER_REQUESTS.labels(policy=policy.id, status="error").inc()
        raise RoutingError("No available model satisfies routing constraints")
    models, scores, downgraded = optimize_for_budget(
        db, models, scores, policy, correlation_id=correlation_id
    )
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
                score.model_id: score.model_dump(mode="json") for score in response.scores
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
        ROUTER_COST.labels(model=model.id, provider=model.provider).inc(score.estimated_cost_usd)
        ROUTER_SCORE.labels(model=model.id).observe(score.total)
    db.commit()
    ROUTER_REQUESTS.labels(policy=policy.id, status="success").inc()
    ROUTER_LATENCY.labels(policy=policy.id).observe(latency_ms / 1000)
    if response.fallback_count:
        ROUTER_FALLBACKS.labels(policy=policy.id).inc(response.fallback_count)
    return response


