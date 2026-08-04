def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """Clamp a numeric metric to its supported range."""

    return max(minimum, min(maximum, value))


def normalize_ratio(numerator: float, denominator: float) -> float:
    """Convert a ratio to a bounded 0–100 score."""

    if denominator <= 0:
        return 0.0
    return clamp((numerator / denominator) * 100.0)


def round_score(value: float) -> float:
    return round(clamp(value), 2)

