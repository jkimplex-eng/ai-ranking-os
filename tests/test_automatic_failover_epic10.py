from datetime import UTC, datetime

from backend.app.llm_router.automatic_failover import (
    FailoverReason,
    classify_failover_reason,
    order_failover_models,
)
from backend.app.llm_router.schemas import (
    ModelCreate,
    ModelRead,
    Pricing,
    ScoreBreakdown,
)
from backend.app.providers.exceptions import ProviderError, ProviderErrorCategory


def model(model_id: str, provider: str) -> ModelRead:
    return ModelRead(
        **ModelCreate(
            id=model_id, provider=provider, display_name=model_id,
            pricing=Pricing(input_per_million=0, output_per_million=0),
            latency_ms=100, quality=0.8, availability=1, context_window=4096,
            hallucination_rate=0.1,
        ).model_dump(),
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )


def test_failover_order_skips_missing_providers_but_preserves_priority() -> None:
    models = [model("gpt", "openai"), model("gemini", "gemini"), model("local", "local")]
    scores = [
        ScoreBreakdown(
            model_id=item.id,
            provider=item.provider,
            total=0.8,
            factors={},
            estimated_cost_usd=0,
        )
        for item in models
    ]
    ordered, _ = order_failover_models(models, scores)
    assert [item.provider for item in ordered] == ["local", "gemini", "openai"]


def test_failover_error_classification() -> None:
    timeout = ProviderError(
        "timeout", category=ProviderErrorCategory.TIMEOUT, provider="ollama", retryable=True
    )
    quota = ProviderError(
        "quota exceeded", category=ProviderErrorCategory.RATE_LIMIT,
        provider="gemini", retryable=True,
    )
    unavailable = ProviderError(
        "network", category=ProviderErrorCategory.NETWORK,
        provider="github", retryable=True,
    )
    assert classify_failover_reason(timeout) == FailoverReason.TIMEOUT
    assert classify_failover_reason(quota) == FailoverReason.QUOTA_EXCEEDED
    assert classify_failover_reason(unavailable) == FailoverReason.UNAVAILABLE
