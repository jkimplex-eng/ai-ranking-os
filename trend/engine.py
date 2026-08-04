from statistics import fmean
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from trend.models import TrendDirection, TrendPoint, TrendSeries, TrendSnapshot
from trend.ports import TrendDataSource, TrendDataUnavailableError
from trend.schemas import MetricTrend, TrendMetric, TrendPointRead, TrendSeriesRead


class TrendEngine:
    MODEL_VERSION = "1.0"
    MOVING_AVERAGE_WINDOW = 3
    STABLE_THRESHOLD = 1.0

    def __init__(self, db: Session, source: TrendDataSource) -> None:
        self.db = db
        self.source = source

    def build(self, entity_id: UUID) -> TrendSeriesRead:
        observations = self.source.history(entity_id)
        if not observations:
            raise TrendDataUnavailableError(f"Entity {entity_id} has no scored observations")

        series = self.db.scalar(
            select(TrendSeries).where(
                TrendSeries.entity_id == entity_id,
                TrendSeries.model_version == self.MODEL_VERSION,
            )
        )
        if series is None:
            series = TrendSeries(
                entity_id=entity_id,
                model_version=self.MODEL_VERSION,
                moving_average_window=self.MOVING_AVERAGE_WINDOW,
            )
            self.db.add(series)
            self.db.flush()

        snapshot = TrendSnapshot(series_id=series.id, source_count=len(observations))
        self.db.add(snapshot)
        self.db.flush()

        for metric in TrendMetric:
            values = [observation.metrics()[metric.value] for observation in observations]
            for index, (observation, value) in enumerate(zip(observations, values, strict=True)):
                previous = values[index - 1] if index else None
                start = max(0, index - self.MOVING_AVERAGE_WINDOW + 1)
                self.db.add(
                    TrendPoint(
                        snapshot_id=snapshot.id,
                        research_id=observation.research_id,
                        metric=metric.value,
                        observed_at=observation.observed_at,
                        value=round(value, 2),
                        moving_average=round(fmean(values[start : index + 1]), 2),
                        percentage_change=self._percentage_change(value, previous),
                        direction=self._direction(value, previous),
                    )
                )
        self.db.commit()
        self.db.refresh(snapshot)
        return self._result(series, snapshot)

    def _result(self, series: TrendSeries, snapshot: TrendSnapshot) -> TrendSeriesRead:
        points = self.db.scalars(
            select(TrendPoint)
            .where(TrendPoint.snapshot_id == snapshot.id)
            .order_by(TrendPoint.metric, TrendPoint.observed_at, TrendPoint.research_id)
        ).all()
        metrics = []
        for metric in TrendMetric:
            metric_points = [point for point in points if point.metric == metric.value]
            items = [
                TrendPointRead(
                    research_id=point.research_id,
                    observed_at=point.observed_at,
                    value=point.value,
                    moving_average=point.moving_average,
                    percentage_change=point.percentage_change,
                    direction=point.direction,
                )
                for point in metric_points
            ]
            metrics.append(
                MetricTrend(
                    entity_id=series.entity_id,
                    series_id=series.id,
                    snapshot_id=snapshot.id,
                    metric=metric,
                    direction=items[-1].direction,
                    points=items,
                )
            )
        return TrendSeriesRead(
            entity_id=series.entity_id,
            series_id=series.id,
            snapshot_id=snapshot.id,
            model_version=series.model_version,
            moving_average_window=series.moving_average_window,
            generated_at=snapshot.built_at,
            metrics=metrics,
        )

    @classmethod
    def _direction(cls, current: float, previous: float | None) -> TrendDirection:
        if previous is None or abs(current - previous) <= cls.STABLE_THRESHOLD:
            return TrendDirection.STABLE
        return TrendDirection.UP if current > previous else TrendDirection.DOWN

    @staticmethod
    def _percentage_change(current: float, previous: float | None) -> float | None:
        if previous is None or previous == 0:
            return None
        return round((current - previous) / abs(previous) * 100, 2)

