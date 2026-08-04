from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from query_intent.models import (
    ConfidenceHistory,
    IntentClassificationRun,
    IntentHistory,
    RoutingMetadataHistory,
)
from query_intent.pipeline import run_pipeline
from query_intent.schemas import IntentInput, IntentResult


class IntentNotFoundError(LookupError):
    """No intent result exists for this request ID."""


class DuplicateIntentRequestError(ValueError):
    """The request ID was already classified."""


def classify(db: Session, payload: IntentInput) -> IntentResult:
    result = run_pipeline(payload)
    run = IntentClassificationRun(
        request_id=result.request_id,
        query=result.query,
        language=result.language.code,
        primary_intent=result.primary_intent,
        confidence=result.confidence,
        output_payload=result.model_dump(mode="json"),
        version=result.version,
        classified_at=result.classified_at,
    )
    db.add(run)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise DuplicateIntentRequestError(
            f"Request {result.request_id} has already been classified"
        ) from error

    db.add_all(
        [
            IntentHistory(
                run_id=run.id,
                request_id=result.request_id,
                intent=candidate.intent,
                subtype=candidate.subtype,
                confidence=candidate.confidence,
                is_primary=candidate.intent == result.primary_intent,
                signals=candidate.signals,
            )
            for candidate in result.intents
        ]
    )
    confidence_rows = []
    score_sources = (
        ("RULE", result.routing.rule_scores),
        ("EMBEDDING", result.routing.embedding_scores),
        ("ENSEMBLE", result.routing.ensemble_scores),
    )
    for source, scores in score_sources:
        confidence_rows.extend(
            ConfidenceHistory(
                run_id=run.id,
                request_id=result.request_id,
                source=source,
                intent=intent,
                confidence=score,
            )
            for intent, score in scores.items()
        )
    confidence_rows.append(
        ConfidenceHistory(
            run_id=run.id,
            request_id=result.request_id,
            source="FINAL",
            intent=result.primary_intent,
            confidence=result.confidence,
        )
    )
    db.add_all(confidence_rows)
    db.add(
        RoutingMetadataHistory(
            run_id=run.id,
            request_id=result.request_id,
            strategy=result.routing.strategy,
            llm_fallback_required=result.routing.llm_fallback_required,
            metadata_payload=result.routing.model_dump(mode="json"),
        )
    )
    db.commit()
    return result


def classify_batch(db: Session, payloads: list[IntentInput]) -> list[IntentResult]:
    return [classify(db, payload) for payload in payloads]


def get_result(db: Session, request_id: str) -> IntentResult:
    query = select(IntentClassificationRun).where(
        IntentClassificationRun.request_id == request_id
    )
    run = db.scalar(query)
    if run is None:
        raise IntentNotFoundError(f"No intent classification for request {request_id}")
    return IntentResult.model_validate(run.output_payload)

