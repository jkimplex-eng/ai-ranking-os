from __future__ import annotations

from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from analytics.ports import AnalyticsRecord
from segmentation.models import SegmentDefinition, SegmentEvaluation, SegmentMembership
from segmentation.schemas import SegmentCreate, SegmentUpdate


class SegmentNotFoundError(LookupError):
    pass


class SegmentCodeConflictError(ValueError):
    pass


class SegmentRepository(Protocol):
    def create(self, payload: SegmentCreate) -> SegmentDefinition: ...
    def get(self, segment_id: int) -> SegmentDefinition: ...
    def list(self, page: int, page_size: int) -> tuple[list[SegmentDefinition], int]: ...
    def update(self, segment_id: int, payload: SegmentUpdate) -> SegmentDefinition: ...
    def delete(self, segment_id: int) -> None: ...
    def save_evaluation(
        self, segment: SegmentDefinition, source_count: int, records: list[AnalyticsRecord]
    ) -> SegmentEvaluation: ...
    def latest_evaluation(self, segment_id: int) -> SegmentEvaluation: ...


class SqlAlchemySegmentRepository(SegmentRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: SegmentCreate) -> SegmentDefinition:
        segment = SegmentDefinition(
            **payload.model_dump(mode="json", exclude={"segment_type"}),
            segment_type=payload.segment_type.value,
        )
        self.db.add(segment)
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise SegmentCodeConflictError(
                f"Segment code {payload.code!r} already exists"
            ) from error
        self.db.refresh(segment)
        return segment

    def get(self, segment_id: int) -> SegmentDefinition:
        segment = self.db.get(SegmentDefinition, segment_id)
        if segment is None:
            raise SegmentNotFoundError(f"Segment {segment_id} not found")
        return segment

    def list(self, page: int, page_size: int) -> tuple[list[SegmentDefinition], int]:
        total = self.db.scalar(select(func.count(SegmentDefinition.id))) or 0
        rows = self.db.scalars(
            select(SegmentDefinition)
            .order_by(SegmentDefinition.created_at.desc(), SegmentDefinition.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(rows), total

    def update(self, segment_id: int, payload: SegmentUpdate) -> SegmentDefinition:
        segment = self.get(segment_id)
        for field, value in payload.model_dump(exclude_unset=True, mode="json").items():
            setattr(segment, field, value)
        self.db.commit()
        self.db.refresh(segment)
        return segment

    def delete(self, segment_id: int) -> None:
        self.db.delete(self.get(segment_id))
        self.db.commit()

    def save_evaluation(
        self, segment: SegmentDefinition, source_count: int, records: list[AnalyticsRecord]
    ) -> SegmentEvaluation:
        evaluation = SegmentEvaluation(
            segment_id=segment.id,
            segment_version=segment.version,
            source_count=source_count,
            matched_count=len(records),
        )
        self.db.add(evaluation)
        self.db.flush()
        for record in records:
            self.db.add(
                SegmentMembership(
                    evaluation_id=evaluation.id,
                    member_key=self._member_key(record),
                    observed_at=record.observed_at,
                    dimensions=record.dimensions,
                    metrics=record.metrics,
                )
            )
        self.db.commit()
        return self.get_evaluation(evaluation.id)

    def get_evaluation(self, evaluation_id: int) -> SegmentEvaluation:
        evaluation = self.db.scalar(
            select(SegmentEvaluation)
            .options(
                selectinload(SegmentEvaluation.segment),
                selectinload(SegmentEvaluation.memberships),
            )
            .where(SegmentEvaluation.id == evaluation_id)
        )
        if evaluation is None:
            raise SegmentNotFoundError(f"Segment evaluation {evaluation_id} not found")
        return evaluation

    def latest_evaluation(self, segment_id: int) -> SegmentEvaluation:
        self.get(segment_id)
        evaluation = self.db.scalar(
            select(SegmentEvaluation)
            .options(
                selectinload(SegmentEvaluation.segment),
                selectinload(SegmentEvaluation.memberships),
            )
            .where(SegmentEvaluation.segment_id == segment_id)
            .order_by(SegmentEvaluation.evaluated_at.desc(), SegmentEvaluation.id.desc())
        )
        if evaluation is None:
            raise SegmentNotFoundError(f"Segment {segment_id} has not been evaluated")
        return evaluation

    @staticmethod
    def _member_key(record: AnalyticsRecord) -> str:
        from hashlib import sha256
        from json import dumps

        identity = dumps(
            {
                "observed_at": record.observed_at.isoformat(),
                "dimensions": record.dimensions,
            },
            sort_keys=True,
        )
        return sha256(identity.encode()).hexdigest()
