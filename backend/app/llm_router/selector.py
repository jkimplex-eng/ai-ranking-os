from sqlalchemy.orm import Session

from backend.app.llm_router.circuit_breaker import allow_request
from backend.app.llm_router.schemas import (
    ModelRead,
    RouteRequest,
    RouterStrategy,
    ScoreBreakdown,
)
from backend.app.llm_router.scoring import score_model
from query_intent.schemas import IntentType


def select_models(
    db: Session,
    models: list[ModelRead],
    request: RouteRequest,
    intent: IntentType,
    weights: dict[str, float],
    required_capabilities: list[str],
) -> tuple[list[ModelRead], list[ScoreBreakdown]]:
    required = set(required_capabilities) | set(request.required_capabilities)
    candidates = [
        model
        for model in models
        if model.status == "ACTIVE"
        and model.availability >= 0.5
        and model.context_window >= request.context_tokens
        and required.issubset(model.capabilities)
        and (request.region is None or model.region == request.region)
        and allow_request(db, model.id)
    ]
    if request.strategy == RouterStrategy.LOCAL_ONLY:
        candidates = [model for model in candidates if model.tier == "LOCAL"]
    elif request.strategy == RouterStrategy.FREE_ONLY:
        candidates = [
            model
            for model in candidates
            if model.pricing.input_per_million == 0
            and model.pricing.output_per_million == 0
        ]
    scores = [
        score_model(model, request, intent, weights)
        for model in candidates
    ]
    by_id = {model.id: model for model in candidates}
    if request.strategy == RouterStrategy.FASTEST:
        scores.sort(key=lambda item: (by_id[item.model_id].latency_ms, -item.total))
    elif request.strategy in {RouterStrategy.CHEAPEST, RouterStrategy.FREE_ONLY}:
        scores.sort(key=lambda item: (item.estimated_cost_usd, -item.total))
    elif request.strategy == RouterStrategy.HIGHEST_QUALITY:
        scores.sort(key=lambda item: (-by_id[item.model_id].quality, -item.total))
    else:
        scores.sort(key=lambda item: (-item.total, item.estimated_cost_usd, item.model_id))
    return [by_id[score.model_id] for score in scores], scores
