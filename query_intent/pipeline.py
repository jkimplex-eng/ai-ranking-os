from datetime import UTC, datetime
from uuid import uuid4

from entity_extraction.pipeline import run_pipeline as extract_entity_pipeline
from entity_extraction.schemas import ExtractionInput
from query_intent.classifier import LLMFallback, classify
from query_intent.constraints import extract_constraints
from query_intent.expected_output import expected_output_for
from query_intent.multilingual import detect_language
from query_intent.schemas import (
    IntentInput,
    IntentResult,
    QueryEntity,
    RoutingMetadata,
)


def run_pipeline(
    payload: IntentInput,
    *,
    now: datetime | None = None,
    llm_fallback: LLMFallback | None = None,
) -> IntentResult:
    classified_at = now or datetime.now(UTC)
    language = detect_language(payload.query)
    entity_result = extract_entity_pipeline(
        ExtractionInput(raw_response=payload.query),
        now=classified_at,
    )
    rule_match, embedding_scores, ensemble = classify(payload.query, llm_fallback)
    used_fallback = bool(
        ensemble.intents and ensemble.intents[0].signals == ["llm_fallback"]
    )
    return IntentResult(
        request_id=payload.request_id or str(uuid4()),
        query=payload.query,
        language=language,
        primary_intent=ensemble.primary_intent,
        intents=ensemble.intents,
        constraints=extract_constraints(payload.query, language.code),
        entities=[
            QueryEntity(
                name=entity.canonical_name,
                entity_type=entity.entity_type,
                confidence=entity.confidence,
                knowledge_graph_id=entity.knowledge_graph_id,
            )
            for entity in entity_result.entities
        ],
        expected_output=expected_output_for(ensemble.primary_intent),
        confidence=ensemble.confidence,
        routing=RoutingMetadata(
            strategy="LLM_FALLBACK" if used_fallback else "RULE_EMBEDDING_ENSEMBLE",
            llm_fallback_required=ensemble.llm_fallback_required,
            rule_scores={intent: round(score, 4) for intent, score in rule_match.scores.items()},
            embedding_scores={
                intent: round(score, 4) for intent, score in embedding_scores.items()
            },
            ensemble_scores={intent: score for intent, score in ensemble.scores.items()},
        ),
        classified_at=classified_at,
    )
