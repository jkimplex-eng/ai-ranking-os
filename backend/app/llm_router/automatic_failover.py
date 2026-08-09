from enum import StrEnum

from backend.app.llm_router.schemas import ModelRead, ScoreBreakdown
from backend.app.providers.exceptions import ProviderError, ProviderErrorCategory

FAILOVER_PROVIDER_ORDER = ("ollama", "local", "groq", "gemini", "google", "github", "openai")


class FailoverReason(StrEnum):
    TIMEOUT = "timeout"
    PROVIDER_ERROR = "provider_error"
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    UNAVAILABLE = "unavailable"


def classify_failover_reason(error: Exception) -> FailoverReason:
    if isinstance(error, ProviderError):
        if error.category == ProviderErrorCategory.TIMEOUT:
            return FailoverReason.TIMEOUT
        if error.category == ProviderErrorCategory.RATE_LIMIT:
            text = str(error).casefold()
            return FailoverReason.QUOTA_EXCEEDED if "quota" in text else FailoverReason.RATE_LIMIT
        if error.category in {ProviderErrorCategory.NETWORK, ProviderErrorCategory.CONFIGURATION}:
            return FailoverReason.UNAVAILABLE
    return FailoverReason.PROVIDER_ERROR


def order_failover_models(
    models: list[ModelRead], scores: list[ScoreBreakdown]
) -> tuple[list[ModelRead], list[ScoreBreakdown]]:
    rank = {provider: index for index, provider in enumerate(FAILOVER_PROVIDER_ORDER)}
    score_by_id = {score.model_id: score for score in scores}
    ordered = sorted(
        models,
        key=lambda model: (
            rank.get(model.provider, len(rank)),
            -score_by_id[model.id].total,
            model.id,
        ),
    )
    return ordered, [score_by_id[model.id] for model in ordered]
