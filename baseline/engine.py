from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from baseline.models import (
    Baseline,
    BaselineSnapshot,
    BaselineUpdatePolicy,
    RegressionEvent,
    RegressionSeverity,
)
from baseline.schemas import (
    BaselineCreate,
    BaselineRead,
    BaselineSnapshotRead,
    EvaluationResult,
    RegressionEventRead,
    RegressionThresholds,
)
from trend.ports import TrendDataSource, TrendObservation


class BaselineNotFoundError(LookupError):
    """No baseline has been configured for the entity."""


class BaselineDataUnavailableError(LookupError):
    """The selected or current scored observation is unavailable."""


class BaselineEngine:
    ALGORITHM_VERSION = "1.0"

    def __init__(self, db: Session, source: TrendDataSource) -> None:
        self.db = db
        self.source = source

    def set(self, entity_id: UUID, payload: BaselineCreate) -> BaselineRead:
        observations = self.source.history(entity_id)
        observation = self._select(observations, payload.research_id, entity_id)
        baseline = self.db.scalar(select(Baseline).where(Baseline.entity_id == entity_id))
        reason = "CREATED"
        if baseline is None:
            baseline = Baseline(
                entity_id=entity_id,
                research_id=observation.research_id,
                update_policy=payload.update_policy,
                thresholds=payload.thresholds.model_dump(),
                algorithm_version=self.ALGORITHM_VERSION,
            )
            self.db.add(baseline)
            self.db.flush()
        else:
            reason = "MANUAL_UPDATE"
            baseline.research_id = observation.research_id
            baseline.update_policy = payload.update_policy
            baseline.thresholds = payload.thresholds.model_dump()
            baseline.algorithm_version = self.ALGORITHM_VERSION
        self._snapshot(baseline, observation, reason)
        self.db.commit()
        return self.get(entity_id)

    def get(self, entity_id: UUID) -> BaselineRead:
        baseline = self.db.scalar(
            select(Baseline)
            .options(selectinload(Baseline.snapshots))
            .where(Baseline.entity_id == entity_id)
        )
        if baseline is None:
            raise BaselineNotFoundError(f"Baseline for entity {entity_id} not found")
        return self._read(baseline)

    def evaluate(self, entity_id: UUID) -> EvaluationResult:
        baseline = self.db.scalar(
            select(Baseline)
            .options(selectinload(Baseline.snapshots))
            .where(Baseline.entity_id == entity_id)
        )
        if baseline is None:
            raise BaselineNotFoundError(f"Baseline for entity {entity_id} not found")
        observations = self.source.history(entity_id)
        current = self._select(observations, None, entity_id)
        snapshots = sorted(baseline.snapshots, key=lambda item: item.id)
        snapshot = snapshots[-1]
        thresholds = RegressionThresholds.model_validate(baseline.thresholds)
        events = []
        baseline_metrics = self._snapshot_metrics(snapshot)
        for metric, current_value in current.metrics().items():
            baseline_value = baseline_metrics[metric]
            decline = round(baseline_value - current_value, 2)
            severity = self._severity(decline, thresholds)
            if severity is None:
                continue
            event = RegressionEvent(
                baseline_id=baseline.id,
                baseline_snapshot_id=snapshot.id,
                current_research_id=current.research_id,
                metric=metric,
                baseline_value=baseline_value,
                current_value=current_value,
                delta=round(current_value - baseline_value, 2),
                severity=severity,
                algorithm_version=self.ALGORITHM_VERSION,
            )
            self.db.add(event)
            events.append(event)
        updated = self._should_update(baseline, snapshot, current)
        if updated and current.research_id != snapshot.research_id:
            baseline.research_id = current.research_id
            self._snapshot(baseline, current, f"AUTO_{baseline.update_policy}")
        else:
            updated = False
        self.db.commit()
        for event in events:
            self.db.refresh(event)
        return EvaluationResult(
            entity_id=entity_id,
            baseline_snapshot_id=snapshot.id,
            baseline_research_id=snapshot.research_id,
            current_research_id=current.research_id,
            algorithm_version=self.ALGORITHM_VERSION,
            baseline_updated=updated,
            regressions=[self._event_read(event) for event in events],
        )

    @staticmethod
    def _select(
        observations: list[TrendObservation], research_id: int | None, entity_id: UUID
    ) -> TrendObservation:
        if research_id is None and observations:
            return observations[-1]
        for observation in observations:
            if observation.research_id == research_id:
                return observation
        raise BaselineDataUnavailableError(
            f"Entity {entity_id} has no scored observation for research {research_id}"
        )

    def _snapshot(
        self, baseline: Baseline, observation: TrendObservation, reason: str
    ) -> BaselineSnapshot:
        snapshot = BaselineSnapshot(
            baseline_id=baseline.id,
            research_id=observation.research_id,
            **observation.metrics(),
            reason=reason,
            algorithm_version=self.ALGORITHM_VERSION,
        )
        self.db.add(snapshot)
        return snapshot

    @staticmethod
    def _severity(
        decline: float, thresholds: RegressionThresholds
    ) -> RegressionSeverity | None:
        if decline >= thresholds.critical:
            return RegressionSeverity.CRITICAL
        if decline >= thresholds.major:
            return RegressionSeverity.MAJOR
        if decline >= thresholds.moderate:
            return RegressionSeverity.MODERATE
        if decline >= thresholds.minor:
            return RegressionSeverity.MINOR
        return None

    @staticmethod
    def _should_update(
        baseline: Baseline, snapshot: BaselineSnapshot, current: TrendObservation
    ) -> bool:
        if baseline.update_policy == BaselineUpdatePolicy.LATEST:
            return True
        return (
            baseline.update_policy == BaselineUpdatePolicy.BEST_VISIBILITY
            and current.visibility > snapshot.visibility
        )

    @staticmethod
    def _snapshot_metrics(snapshot: BaselineSnapshot) -> dict[str, float]:
        return {
            "visibility": snapshot.visibility,
            "mention": snapshot.mention,
            "recommendation": snapshot.recommendation,
            "citation": snapshot.citation,
            "coverage": snapshot.coverage,
            "confidence": snapshot.confidence,
        }

    @classmethod
    def _read(cls, baseline: Baseline) -> BaselineRead:
        return BaselineRead(
            id=baseline.id,
            entity_id=baseline.entity_id,
            research_id=baseline.research_id,
            update_policy=baseline.update_policy,
            thresholds=baseline.thresholds,
            algorithm_version=baseline.algorithm_version,
            created_at=baseline.created_at,
            updated_at=baseline.updated_at,
            snapshots=[
                BaselineSnapshotRead(
                    id=snapshot.id,
                    research_id=snapshot.research_id,
                    metrics=cls._snapshot_metrics(snapshot),
                    reason=snapshot.reason,
                    algorithm_version=snapshot.algorithm_version,
                    created_at=snapshot.created_at,
                )
                for snapshot in sorted(baseline.snapshots, key=lambda item: item.id)
            ],
        )

    @staticmethod
    def _event_read(event: RegressionEvent) -> RegressionEventRead:
        return RegressionEventRead(
            id=event.id,
            metric=event.metric,
            baseline_value=event.baseline_value,
            current_value=event.current_value,
            delta=event.delta,
            severity=event.severity,
            algorithm_version=event.algorithm_version,
            created_at=event.created_at,
        )

