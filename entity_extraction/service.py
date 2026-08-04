from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from entity_extraction.models import (
    EntityExtractionRun,
    EntityHistory,
    RelationHistory,
    ResolutionLogHistory,
)
from entity_extraction.pipeline import run_pipeline
from entity_extraction.schemas import ExtractionInput, ExtractionResult


class ExtractionNotFoundError(LookupError):
    """No extraction exists for the response ID."""


class DuplicateResponseError(ValueError):
    """The response ID was already processed."""


def extract(db: Session, payload: ExtractionInput) -> ExtractionResult:
    result = run_pipeline(payload)
    run = EntityExtractionRun(
        response_id=result.response_id,
        model=payload.model,
        raw_response=payload.raw_response,
        output_payload=result.model_dump(mode="json"),
        version=result.version,
        processed_at=result.processed_at,
    )
    db.add(run)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise DuplicateResponseError(
            f"Response {result.response_id} has already been processed"
        ) from error

    db.add_all(
        [
            EntityHistory(
                run_id=run.id,
                response_id=result.response_id,
                entity_id=entity.entity_id,
                name=entity.name,
                canonical_name=entity.canonical_name,
                entity_type=entity.entity_type,
                confidence=entity.confidence,
                aliases=entity.aliases,
                knowledge_graph_id=entity.knowledge_graph_id,
            )
            for entity in result.entities
        ]
    )
    db.add_all(
        [
            RelationHistory(
                run_id=run.id,
                response_id=result.response_id,
                relation_id=relation.relation_id,
                source_entity_id=relation.source_entity_id,
                target_entity_id=relation.target_entity_id,
                relation_type=relation.relation_type,
                confidence=relation.confidence,
            )
            for relation in result.relations
        ]
    )
    db.add_all(
        [
            ResolutionLogHistory(
                run_id=run.id,
                response_id=result.response_id,
                stage=log.stage,
                action=log.action,
                details=log.details,
            )
            for log in result.resolution_logs
        ]
    )
    db.commit()
    return result


def extract_batch(
    db: Session,
    payloads: list[ExtractionInput],
) -> list[ExtractionResult]:
    return [extract(db, payload) for payload in payloads]


def get_extraction(db: Session, response_id: str) -> ExtractionResult:
    query = select(EntityExtractionRun).where(EntityExtractionRun.response_id == response_id)
    run = db.scalar(query)
    if run is None:
        raise ExtractionNotFoundError(f"No extraction for response {response_id}")
    return ExtractionResult.model_validate(run.output_payload)

