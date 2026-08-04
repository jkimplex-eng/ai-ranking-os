from collections.abc import Mapping

DEFAULT_WEIGHT_VERSION = "1.0"
DEFAULT_WEIGHTS: dict[str, float] = {
    "mention_frequency": 0.20,
    "recommendation_position": 0.15,
    "citation_count": 0.10,
    "citation_authority": 0.15,
    "cross_model_presence": 0.15,
    "consistency": 0.10,
    "entity_confidence": 0.10,
    "freshness": 0.05,
}


def validate_weights(weights: Mapping[str, float]) -> dict[str, float]:
    missing = set(DEFAULT_WEIGHTS) - set(weights)
    unexpected = set(weights) - set(DEFAULT_WEIGHTS)
    if missing or unexpected:
        raise ValueError(
            f"Invalid weight keys; missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )
    if any(value < 0 for value in weights.values()):
        raise ValueError("Weights cannot be negative")
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"Weights must sum to 1.0, got {total}")
    return dict(weights)

