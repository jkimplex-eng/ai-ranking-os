import math
import statistics
from datetime import UTC, datetime

from ai_visibility.normalization import normalize_ratio, round_score
from ai_visibility.schemas import ObservationInput, VisibilityInput

POSITION_SCORES = {1: 100.0, 2: 75.0, 3: 50.0, 4: 25.0}
FRESHNESS_HALF_LIFE_DAYS = 30.0


def mention_frequency(observations: list[ObservationInput]) -> float:
    mentions = sum(item.mentioned for item in observations)
    return round_score(normalize_ratio(mentions, len(observations)))


def recommendation_position(observations: list[ObservationInput]) -> float:
    mentioned = [item for item in observations if item.mentioned]
    if not mentioned:
        return 0.0
    scores = [
        POSITION_SCORES.get(item.recommendation_position or 5, 0.0)
        for item in mentioned
    ]
    return round_score(statistics.fmean(scores))


def citation_count(observations: list[ObservationInput]) -> float:
    citations = sum(len(item.citations) for item in observations)
    saturation_target = len(observations) * 3
    return round_score(normalize_ratio(citations, saturation_target))


def citation_authority(observations: list[ObservationInput]) -> float:
    authorities = [
        citation.authority
        for observation in observations
        for citation in observation.citations
    ]
    if not authorities:
        return 0.0
    return round_score(statistics.fmean(authorities) * 100.0)


def cross_model_presence(observations: list[ObservationInput]) -> float:
    models = {item.model.lower() for item in observations}
    present_models = {item.model.lower() for item in observations if item.mentioned}
    return round_score(normalize_ratio(len(present_models), len(models)))


def consistency(observations: list[ObservationInput]) -> float:
    model_rates: list[float] = []
    models = {item.model.lower() for item in observations}
    for model in models:
        results = [item.mentioned for item in observations if item.model.lower() == model]
        model_rates.append(sum(results) / len(results))
    if len(model_rates) <= 1:
        return 100.0
    return round_score((1.0 - statistics.pstdev(model_rates)) * 100.0)


def entity_confidence(observations: list[ObservationInput]) -> float:
    return round_score(statistics.fmean(item.entity_confidence for item in observations) * 100.0)


def freshness(observations: list[ObservationInput], *, now: datetime) -> float:
    timestamped = [item.observed_at for item in observations if item.observed_at is not None]
    if not timestamped:
        return 50.0
    scores = []
    for observed_at in timestamped:
        assert observed_at is not None
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=UTC)
        age_days = max(0.0, (now - observed_at).total_seconds() / 86_400)
        scores.append(math.exp(-math.log(2) * age_days / FRESHNESS_HALF_LIFE_DAYS) * 100.0)
    return round_score(statistics.fmean(scores))


def calculate_metrics(
    payload: VisibilityInput,
    *,
    now: datetime | None = None,
) -> dict[str, float]:
    reference_time = now or datetime.now(UTC)
    observations = payload.observations
    return {
        "mention_frequency": mention_frequency(observations),
        "recommendation_position": recommendation_position(observations),
        "citation_count": citation_count(observations),
        "citation_authority": citation_authority(observations),
        "cross_model_presence": cross_model_presence(observations),
        "consistency": consistency(observations),
        "entity_confidence": entity_confidence(observations),
        "freshness": freshness(observations, now=reference_time),
    }
