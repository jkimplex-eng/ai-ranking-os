from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_visibility.models import VisibilityCalculation, VisibilityWeightSet
from ai_visibility.pipeline import run_pipeline
from ai_visibility.schemas import VisibilityInput, VisibilityResult
from ai_visibility.weights import (
    DEFAULT_WEIGHT_VERSION,
    DEFAULT_WEIGHTS,
    validate_weights,
)


class VisibilityNotFoundError(LookupError):
    """No calculation exists for the requested entity."""


def _active_weight_set(db: Session) -> VisibilityWeightSet:
    query = (
        select(VisibilityWeightSet)
        .where(VisibilityWeightSet.is_active.is_(True))
        .order_by(VisibilityWeightSet.created_at.desc(), VisibilityWeightSet.id.desc())
    )
    weight_set = db.scalar(query)
    if weight_set is None:
        weight_set = VisibilityWeightSet(
            version=DEFAULT_WEIGHT_VERSION,
            weights=DEFAULT_WEIGHTS,
            is_active=True,
        )
        db.add(weight_set)
        db.flush()
    validate_weights(weight_set.weights)
    return weight_set


def calculate(db: Session, payload: VisibilityInput) -> VisibilityResult:
    weight_set = _active_weight_set(db)
    result = run_pipeline(
        payload,
        weights=weight_set.weights,
        version=weight_set.version,
    )
    db.add(
        VisibilityCalculation(
            entity_id=result.entity_id,
            entity=result.entity,
            visibility_score=result.visibility_score,
            confidence=result.confidence,
            metrics=result.metrics,
            weights=result.weights,
            weight_version=result.version,
            input_payload=payload.model_dump(mode="json"),
            calculated_at=result.calculated_at,
        )
    )
    db.commit()
    return result


def calculate_batch(
    db: Session,
    payloads: list[VisibilityInput],
) -> list[VisibilityResult]:
    return [calculate(db, payload) for payload in payloads]


def get_latest(db: Session, entity_id: str) -> VisibilityResult:
    query = (
        select(VisibilityCalculation)
        .where(VisibilityCalculation.entity_id == entity_id)
        .order_by(
            VisibilityCalculation.calculated_at.desc(),
            VisibilityCalculation.id.desc(),
        )
    )
    calculation = db.scalar(query)
    if calculation is None:
        raise VisibilityNotFoundError(f"No visibility calculation for entity {entity_id}")
    return VisibilityResult(
        entity_id=calculation.entity_id,
        entity=calculation.entity,
        visibility_score=calculation.visibility_score,
        confidence=calculation.confidence,
        metrics=calculation.metrics,
        weights=calculation.weights,
        version=calculation.weight_version,
        calculated_at=calculation.calculated_at,
    )
