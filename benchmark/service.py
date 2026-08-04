from collections import defaultdict

from analytics.ports import AnalyticsDataSource
from benchmark.models import BenchmarkRun
from benchmark.repository import BenchmarkRepository
from benchmark.schemas import (
    BenchmarkEntryRead,
    BenchmarkRequest,
    BenchmarkResult,
    BenchmarkRunPage,
    BenchmarkRunSummary,
    MetricBenchmark,
)


class BenchmarkDataUnavailableError(LookupError):
    pass


class BenchmarkService:
    ENGINE_VERSION = "1.0"

    def __init__(self, source: AnalyticsDataSource, repository: BenchmarkRepository) -> None:
        self.source = source
        self.repository = repository

    def execute(self, request: BenchmarkRequest) -> BenchmarkResult:
        records = self.source.records(request.date_from, request.date_to)
        selected = set(request.entity_ids)
        grouped = defaultdict(list)
        for record in records:
            entity_id = record.dimensions.get("entity_id", "")
            if entity_id and (not selected or entity_id in selected):
                grouped[entity_id].append(record)
        if not grouped:
            raise BenchmarkDataUnavailableError("No benchmark observations match the request")
        averages = {
            entity_id: {
                metric: round(
                    sum(record.metrics[metric] for record in observations) / len(observations), 6
                )
                for metric in request.metrics
                if all(metric in record.metrics for record in observations)
            }
            for entity_id, observations in grouped.items()
        }
        missing = [
            entity for entity, values in averages.items() if len(values) != len(request.metrics)
        ]
        if missing:
            raise BenchmarkDataUnavailableError(
                f"Incomplete benchmark metrics for: {', '.join(sorted(missing))}"
            )
        metric_results: dict[str, dict[str, dict]] = defaultdict(dict)
        for metric in request.metrics:
            values = {entity: scores[metric] for entity, scores in averages.items()}
            population_average = sum(values.values()) / len(values)
            leader = max(values.values())
            ranks = self._ranks(values)
            for entity_id, value in values.items():
                metric_results[entity_id][metric] = MetricBenchmark(
                    value=value,
                    rank=ranks[entity_id],
                    percentile=self._percentile(ranks[entity_id], len(values)),
                    population_average=round(population_average, 6),
                    delta_from_average=round(value - population_average, 6),
                    leader_value=leader,
                    delta_from_leader=round(value - leader, 6),
                ).model_dump(mode="json")
        overall = {
            entity: round(sum(scores.values()) / len(request.metrics), 6)
            for entity, scores in averages.items()
        }
        overall_ranks = self._ranks(overall)
        entries = [
            {
                "entity_id": entity,
                "observation_count": len(grouped[entity]),
                "metric_results": metric_results[entity],
                "overall_score": overall[entity],
                "overall_rank": overall_ranks[entity],
                "overall_percentile": self._percentile(overall_ranks[entity], len(overall)),
            }
            for entity in sorted(overall, key=lambda item: (overall_ranks[item], item))
        ]
        return self._read(self.repository.create(request, entries))

    def get(self, run_id: int) -> BenchmarkResult:
        return self._read(self.repository.get(run_id))

    def list(self, page: int, page_size: int) -> BenchmarkRunPage:
        rows, total = self.repository.list(page, page_size)
        return BenchmarkRunPage(
            page=page,
            page_size=page_size,
            total=total,
            items=[
                BenchmarkRunSummary(
                    id=row.id,
                    engine_version=row.engine_version,
                    metrics=row.metrics,
                    entity_count=row.entity_count,
                    calculated_at=row.calculated_at,
                )
                for row in rows
            ],
        )

    @staticmethod
    def _ranks(values: dict[str, float]) -> dict[str, int]:
        ordered = sorted(values.values(), reverse=True)
        return {entity: ordered.index(value) + 1 for entity, value in values.items()}

    @staticmethod
    def _percentile(rank: int, count: int) -> float:
        return 100.0 if count == 1 else round(100 * (count - rank) / (count - 1), 6)

    @staticmethod
    def _read(run: BenchmarkRun) -> BenchmarkResult:
        return BenchmarkResult(
            id=run.id,
            engine_version=run.engine_version,
            metrics=run.metrics,
            entity_count=run.entity_count,
            date_from=run.date_from,
            date_to=run.date_to,
            calculated_at=run.calculated_at,
            entries=[
                BenchmarkEntryRead(
                    entity_id=entry.entity_id,
                    observation_count=entry.observation_count,
                    metrics={
                        key: MetricBenchmark.model_validate(value)
                        for key, value in entry.metric_results.items()
                    },
                    overall_score=entry.overall_score,
                    overall_rank=entry.overall_rank,
                    overall_percentile=entry.overall_percentile,
                )
                for entry in sorted(
                    run.entries, key=lambda item: (item.overall_rank, item.entity_id)
                )
            ],
        )
