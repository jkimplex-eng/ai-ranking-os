from dataclasses import dataclass

from query_intent.rules import RuleMatch
from query_intent.schemas import IntentCandidate, IntentType


@dataclass(frozen=True)
class EnsembleResult:
    primary_intent: IntentType
    intents: list[IntentCandidate]
    scores: dict[IntentType, float]
    confidence: float
    llm_fallback_required: bool


def aggregate(
    rule_match: RuleMatch,
    embedding_scores: dict[IntentType, float],
) -> EnsembleResult:
    scores = {
        intent: round(0.65 * rule_match.scores[intent] + 0.35 * embedding_scores[intent], 4)
        for intent in IntentType
    }
    ranked = sorted(scores, key=scores.get, reverse=True)  # type: ignore[arg-type]
    primary = ranked[0]
    primary_score = scores[primary]
    second_score = scores[ranked[1]]
    threshold = max(0.2, primary_score * 0.6)
    selected = [intent for intent in ranked[:3] if scores[intent] >= threshold]
    confidence = min(1.0, 0.7 * primary_score + 0.3 * max(0.0, primary_score - second_score))
    candidates = [
        IntentCandidate(
            intent=intent,
            subtype=rule_match.subtypes[intent],
            confidence=round(scores[intent], 4),
            signals=rule_match.signals[intent],
        )
        for intent in selected
    ]
    fallback = primary_score < 0.35 or (primary_score - second_score) < 0.05
    return EnsembleResult(
        primary_intent=primary,
        intents=candidates,
        scores=scores,
        confidence=round(confidence, 4),
        llm_fallback_required=fallback,
    )

