from datetime import UTC, datetime

from ai_visibility.calculator import calculate_visibility_score
from ai_visibility.confidence import calculate_confidence
from ai_visibility.metrics import calculate_metrics
from ai_visibility.schemas import VisibilityInput, VisibilityResult
from ai_visibility.weights import DEFAULT_WEIGHT_VERSION, DEFAULT_WEIGHTS


def run_pipeline(
    payload: VisibilityInput,
    *,
    weights: dict[str, float] | None = None,
    version: str = DEFAULT_WEIGHT_VERSION,
    now: datetime | None = None,
) -> VisibilityResult:
    calculated_at = now or datetime.now(UTC)
    active_weights = weights or DEFAULT_WEIGHTS
    metrics = calculate_metrics(payload, now=calculated_at)
    return VisibilityResult(
        entity_id=payload.entity_id or "entity",
        entity=payload.entity,
        visibility_score=calculate_visibility_score(metrics, active_weights),
        confidence=calculate_confidence(payload),
        metrics=metrics,
        weights=active_weights,
        version=version,
        calculated_at=calculated_at,
    )
