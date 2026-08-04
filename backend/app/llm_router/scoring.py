from backend.app.llm_router.schemas import ModelRead, RouteRequest, ScoreBreakdown
from query_intent.schemas import IntentType

INTENT_CAPABILITIES = {
    IntentType.RESEARCH: {"research", "citations", "web"},
    IntentType.TRANSACTIONAL: {"tools"},
    IntentType.HOW_TO: {"chat", "coding"},
    IntentType.TROUBLESHOOTING: {"coding", "tools"},
    IntentType.COMPARISON: {"research", "chat"},
    IntentType.RECOMMENDATION: {"research", "chat"},
}


def estimate_cost(
    model: ModelRead,
    input_tokens: int,
    output_tokens: int,
) -> float:
    return (
        input_tokens * model.pricing.input_per_million
        + output_tokens * model.pricing.output_per_million
    ) / 1_000_000


def score_model(
    model: ModelRead,
    request: RouteRequest,
    intent: IntentType,
    weights: dict[str, float],
) -> ScoreBreakdown:
    intent_caps = INTENT_CAPABILITIES.get(intent, {"chat"})
    factors = {
        "intent": len(intent_caps & set(model.capabilities)) / len(intent_caps),
        "cost": 1.0
        / (1.0 + estimate_cost(model, request.context_tokens, request.max_output_tokens) * 100),
        "latency": max(0.0, 1.0 - model.latency_ms / 2500),
        "quality": model.quality,
        "context": min(1.0, model.context_window / max(1, request.context_tokens)),
        "hallucination": 1.0 - model.hallucination_rate,
        "domain": 1.0 if request.domain in model.domains or "general" in model.domains else 0.2,
        "language": 1.0 if (request.language or "en") in model.languages else 0.1,
        "region": 1.0 if request.region is None or request.region == model.region else 0.0,
        "success": model.success_probability,
    }
    total = sum(factors[name] * weights.get(name, 0) for name in factors)
    return ScoreBreakdown(
        model_id=model.id,
        provider=model.provider,
        total=round(total, 6),
        factors={name: round(value, 6) for name, value in factors.items()},
        estimated_cost_usd=round(
            estimate_cost(model, request.context_tokens, request.max_output_tokens),
            8,
        ),
    )
