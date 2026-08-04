from typing import Protocol

from query_intent.embeddings import classify_with_embeddings
from query_intent.ensemble import EnsembleResult, aggregate
from query_intent.rules import RuleMatch, classify_with_rules
from query_intent.schemas import IntentCandidate, IntentType


class LLMFallback(Protocol):
    def classify(self, query: str) -> tuple[IntentType, str, float]: ...


def classify(
    query: str,
    llm_fallback: LLMFallback | None = None,
) -> tuple[RuleMatch, dict[IntentType, float], EnsembleResult]:
    rule_match = classify_with_rules(query)
    embedding_scores = classify_with_embeddings(query)
    ensemble = aggregate(rule_match, embedding_scores)
    if ensemble.llm_fallback_required and llm_fallback is not None:
        intent, subtype, confidence = llm_fallback.classify(query)
        scores = dict(ensemble.scores)
        scores[intent] = max(scores[intent], confidence)
        ensemble = EnsembleResult(
            primary_intent=intent,
            intents=[
                IntentCandidate(
                    intent=intent,
                    subtype=subtype,
                    confidence=confidence,
                    signals=["llm_fallback"],
                )
            ],
            scores=scores,
            confidence=confidence,
            llm_fallback_required=False,
        )
    return rule_match, embedding_scores, ensemble
