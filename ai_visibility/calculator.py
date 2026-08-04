from collections.abc import Mapping

from ai_visibility.normalization import round_score
from ai_visibility.weights import validate_weights


def calculate_visibility_score(
    metrics: Mapping[str, float],
    weights: Mapping[str, float],
) -> float:
    validated_weights = validate_weights(weights)
    missing = set(validated_weights) - set(metrics)
    if missing:
        raise ValueError(f"Metrics are missing required keys: {sorted(missing)}")
    score = sum(metrics[name] * weight for name, weight in validated_weights.items())
    return round_score(score)

