import statistics

from ai_visibility.schemas import VisibilityInput


def calculate_confidence(payload: VisibilityInput) -> float:
    observations = payload.observations
    sample_coverage = min(1.0, len(observations) / 10)
    model_coverage = min(1.0, len({item.model.lower() for item in observations}) / 5)
    optional_fields = [
        (
            item.recommendation_position is not None,
            bool(item.citations),
            item.observed_at is not None,
        )
        for item in observations
    ]
    completeness = sum(sum(fields) for fields in optional_fields) / (len(observations) * 3)
    extraction_confidence = statistics.fmean(
        item.entity_confidence for item in observations
    )
    confidence = (
        0.35 * sample_coverage
        + 0.25 * model_coverage
        + 0.25 * completeness
        + 0.15 * extraction_confidence
    )
    return round(max(0.0, min(1.0, confidence)), 4)

