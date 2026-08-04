from __future__ import annotations

from analytics.ports import AnalyticsDataSource, AnalyticsRecord
from analytics.schemas import AnalyticsFilter, FilterOperator
from segmentation.models import SegmentDefinition, SegmentEvaluation
from segmentation.repository import SegmentRepository
from segmentation.schemas import (
    SegmentCreate,
    SegmentEvaluationRead,
    SegmentMemberRead,
    SegmentPage,
    SegmentRead,
    SegmentType,
    SegmentTypeRead,
    SegmentUpdate,
)


class InactiveSegmentError(ValueError):
    pass


class SegmentService:
    def __init__(self, source: AnalyticsDataSource, repository: SegmentRepository) -> None:
        self.source = source
        self.repository = repository

    def create(self, payload: SegmentCreate) -> SegmentRead:
        return self._read(self.repository.create(payload))

    def get(self, segment_id: int) -> SegmentRead:
        return self._read(self.repository.get(segment_id))

    def list(self, page: int, page_size: int) -> SegmentPage:
        rows, total = self.repository.list(page, page_size)
        return SegmentPage(
            page=page,
            page_size=page_size,
            total=total,
            items=[self._read(row) for row in rows],
        )

    def update(self, segment_id: int, payload: SegmentUpdate) -> SegmentRead:
        current = self.repository.get(segment_id)
        rules = payload.rules or [AnalyticsFilter.model_validate(rule) for rule in current.rules]
        segment_type = SegmentType(current.segment_type)
        dimension = segment_type.dimension
        if dimension and not any(rule.field == dimension for rule in rules):
            raise ValueError(f"{segment_type.value} segment requires a {dimension!r} rule")
        return self._read(self.repository.update(segment_id, payload))

    def delete(self, segment_id: int) -> None:
        self.repository.delete(segment_id)

    def evaluate(self, segment_id: int) -> SegmentEvaluationRead:
        segment = self.repository.get(segment_id)
        if not segment.is_active:
            raise InactiveSegmentError(f"Segment {segment_id} is inactive")
        records = self.source.records()
        rules = [AnalyticsFilter.model_validate(rule) for rule in segment.rules]
        matched = [record for record in records if self._matches(record, rules)]
        evaluation = self.repository.save_evaluation(segment, len(records), matched)
        return self._evaluation_read(evaluation)

    def latest_memberships(self, segment_id: int) -> SegmentEvaluationRead:
        return self._evaluation_read(self.repository.latest_evaluation(segment_id))

    @staticmethod
    def types() -> list[SegmentTypeRead]:
        return [
            SegmentTypeRead(
                type=segment_type,
                dimension=segment_type.dimension,
                custom=segment_type is SegmentType.CUSTOM,
            )
            for segment_type in SegmentType
        ]

    @staticmethod
    def _matches(record: AnalyticsRecord, rules: list[AnalyticsFilter]) -> bool:
        for rule in rules:
            actual = record.metrics.get(rule.field, record.dimensions.get(rule.field))
            expected = rule.value
            if rule.operator is FilterOperator.EQ and actual != expected:
                return False
            if rule.operator is FilterOperator.NE and actual == expected:
                return False
            in_matches = actual in expected if isinstance(expected, list) else actual == expected
            if rule.operator is FilterOperator.IN and not in_matches:
                return False
            if rule.operator is FilterOperator.NOT_IN and in_matches:
                return False
            if (
                rule.operator is FilterOperator.CONTAINS
                and str(expected).casefold() not in str(actual or "").casefold()
            ):
                return False
            if rule.operator in {FilterOperator.GTE, FilterOperator.LTE}:
                if actual is None or isinstance(expected, list):
                    return False
                try:
                    if rule.operator is FilterOperator.GTE and actual < expected:
                        return False
                    if rule.operator is FilterOperator.LTE and actual > expected:
                        return False
                except TypeError:
                    return False
        return True

    @staticmethod
    def _read(segment: SegmentDefinition) -> SegmentRead:
        return SegmentRead(
            id=segment.id,
            code=segment.code,
            name=segment.name,
            segment_type=SegmentType(segment.segment_type),
            rules=[AnalyticsFilter.model_validate(rule) for rule in segment.rules],
            version=segment.version,
            is_active=segment.is_active,
            created_at=segment.created_at,
            updated_at=segment.updated_at,
        )

    @staticmethod
    def _evaluation_read(evaluation: SegmentEvaluation) -> SegmentEvaluationRead:
        return SegmentEvaluationRead(
            id=evaluation.id,
            segment_id=evaluation.segment_id,
            segment_code=evaluation.segment.code,
            segment_version=evaluation.segment_version,
            source_count=evaluation.source_count,
            matched_count=evaluation.matched_count,
            evaluated_at=evaluation.evaluated_at,
            members=[
                SegmentMemberRead(
                    member_key=item.member_key,
                    observed_at=item.observed_at,
                    dimensions=item.dimensions,
                    metrics=item.metrics,
                )
                for item in sorted(evaluation.memberships, key=lambda member: member.member_key)
            ],
        )
