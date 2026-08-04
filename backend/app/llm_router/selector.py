from sqlalchemy.orm import Session

from backend.app.llm_router.circuit_breaker import allow_request
from backend.app.llm_router.schemas import ModelRead, RouteRequest, ScoreBreakdown
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
    scores = [
        score_model(model, request, intent, weights)
        for model in candidates
    ]
    scores.sort(key=lambda item: (-item.total, item.estimated_cost_usd, item.model_id))
    by_id = {model.id: model for model in candidates}
    return [by_id[score.model_id] for score in scores], scores
