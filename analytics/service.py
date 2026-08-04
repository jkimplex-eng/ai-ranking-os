from collections import defaultdict
from datetime import datetime, timedelta
from math import sqrt

from analytics.ports import AnalyticsDataSource, AnalyticsRecord
from analytics.repository import AnalyticsRepository
from analytics.schemas import (
    AnalyticsFilter,
    AnalyticsGroup,
    AnalyticsQuery,
    AnalyticsResult,
    AnalyticsRunPage,
    AnalyticsRunSummary,
    FilterOperator,
    MetricStatistics,
    Statistic,
    StoredAnalyticsRun,
    TimeInterval,
)


class AnalyticsMetricNotFoundError(ValueError):
    """A requested metric does not exist in the selected records."""


class AnalyticsService:
    ENGINE_VERSION = "1.0"

    def __init__(self, source: AnalyticsDataSource, repository: AnalyticsRepository) -> None:
        self.source = source
        self.repository = repository

    def execute(self, query: AnalyticsQuery) -> AnalyticsResult:
        source_records = self.source.records(query.date_from, query.date_to)
        records = [record for record in source_records if self._matches(record, query.filters)]
        available_metrics = {key for record in records for key in record.metrics}
        missing = set(query.metrics) - available_metrics
        if missing and records:
            raise AnalyticsMetricNotFoundError(f"Unknown metrics: {', '.join(sorted(missing))}")
        buckets: dict[
            tuple[tuple[tuple[str, str], ...], datetime | None], list[AnalyticsRecord]
        ] = defaultdict(list)
        for record in records:
            dimensions = tuple(
                (field, record.dimensions.get(field, "")) for field in query.group_by
            )
            interval_start = self._bucket(record.observed_at, query.interval)
            buckets[(dimensions, interval_start)].append(record)
        groups = [
            self._aggregate(dimensions, interval_start, grouped, query)
            for (dimensions, interval_start), grouped in sorted(
                buckets.items(), key=lambda item: self._sort_key(item[0])
            )
        ]
        result_payload = {
            "groups": [group.model_dump(mode="json") for group in groups],
        }
        run = self.repository.create(
            engine_version=self.ENGINE_VERSION,
            query_payload=query.model_dump(mode="json"),
            result_payload=result_payload,
            source_record_count=len(records),
            group_count=len(groups),
        )
        return AnalyticsResult(
            run_id=run.id,
            engine_version=run.engine_version,
            source_record_count=run.source_record_count,
            group_count=run.group_count,
            query=query,
            groups=groups,
            calculated_at=run.calculated_at,
        )

    def get(self, run_id: int) -> AnalyticsResult:
        run = self.repository.get(run_id)
        query = AnalyticsQuery.model_validate(run.query_payload)
        groups = [AnalyticsGroup.model_validate(item) for item in run.result_payload["groups"]]
        return AnalyticsResult(
            run_id=run.id,
            engine_version=run.engine_version,
            source_record_count=run.source_record_count,
            group_count=run.group_count,
            query=query,
            groups=groups,
            calculated_at=run.calculated_at,
        )

    def list(self, page: int, page_size: int) -> AnalyticsRunPage:
        runs, total = self.repository.list(page, page_size)
        return AnalyticsRunPage(
            page=page,
            page_size=page_size,
            total=total,
            items=[
                AnalyticsRunSummary(
                    id=run.id,
                    engine_version=run.engine_version,
                    source_record_count=run.source_record_count,
                    group_count=run.group_count,
                    calculated_at=run.calculated_at,
                )
                for run in runs
            ],
        )

    @staticmethod
    def stored(run) -> StoredAnalyticsRun:
        return StoredAnalyticsRun.model_validate(run)

    def _aggregate(
        self,
        dimensions: tuple[tuple[str, str], ...],
        interval_start: datetime | None,
        records: list[AnalyticsRecord],
        query: AnalyticsQuery,
    ) -> AnalyticsGroup:
        metrics = {}
        for metric in query.metrics:
            values = [record.metrics[metric] for record in records if metric in record.metrics]
            metrics[metric] = MetricStatistics(
                values={
                    statistic: self._statistic(values, statistic) for statistic in query.statistics
                }
            )
        return AnalyticsGroup(
            dimensions=dict(dimensions),
            interval_start=interval_start,
            record_count=len(records),
            metrics=metrics,
        )

    @staticmethod
    def _statistic(values: list[float], statistic: Statistic) -> float | int:
        if statistic is Statistic.COUNT:
            return len(values)
        if not values:
            return 0.0
        ordered = sorted(values)
        if statistic is Statistic.SUM:
            return round(sum(values), 6)
        if statistic is Statistic.AVG:
            return round(sum(values) / len(values), 6)
        if statistic is Statistic.MIN:
            return min(values)
        if statistic is Statistic.MAX:
            return max(values)
        if statistic is Statistic.MEDIAN:
            return AnalyticsService._percentile(ordered, 0.5)
        if statistic is Statistic.STDDEV:
            average = sum(values) / len(values)
            return round(sqrt(sum((value - average) ** 2 for value in values) / len(values)), 6)
        percentiles = {
            Statistic.P25: 0.25,
            Statistic.P75: 0.75,
            Statistic.P90: 0.90,
            Statistic.P95: 0.95,
        }
        return AnalyticsService._percentile(ordered, percentiles[statistic])

    @staticmethod
    def _percentile(ordered: list[float], percentile: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * percentile
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = position - lower
        return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction, 6)

    @staticmethod
    def _bucket(value: datetime, interval: TimeInterval) -> datetime | None:
        if interval is TimeInterval.NONE:
            return None
        base = value.replace(minute=0, second=0, microsecond=0)
        if interval is TimeInterval.HOUR:
            return base
        base = base.replace(hour=0)
        if interval is TimeInterval.DAY:
            return base
        if interval is TimeInterval.WEEK:
            return base - timedelta(days=base.weekday())
        return base.replace(day=1)

    @staticmethod
    def _matches(record: AnalyticsRecord, filters: list[AnalyticsFilter]) -> bool:
        for criterion in filters:
            actual = record.metrics.get(criterion.field, record.dimensions.get(criterion.field))
            expected = criterion.value
            if not AnalyticsService._compare(actual, criterion.operator, expected):
                return False
        return True

    @staticmethod
    def _compare(actual, operator: FilterOperator, expected) -> bool:
        if operator is FilterOperator.EQ:
            return actual == expected
        if operator is FilterOperator.NE:
            return actual != expected
        if operator is FilterOperator.IN:
            return actual in expected if isinstance(expected, list) else actual == expected
        if operator is FilterOperator.NOT_IN:
            return actual not in expected if isinstance(expected, list) else actual != expected
        if operator is FilterOperator.CONTAINS:
            return str(expected).casefold() in str(actual or "").casefold()
        if actual is None or isinstance(expected, list):
            return False
        try:
            return actual >= expected if operator is FilterOperator.GTE else actual <= expected
        except TypeError:
            return False

    @staticmethod
    def _sort_key(key):
        dimensions, interval_start = key
        return (interval_start is None, interval_start or datetime.min, dimensions)
