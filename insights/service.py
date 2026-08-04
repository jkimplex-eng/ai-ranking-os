from __future__ import annotations

from collections import defaultdict
from math import sqrt
from typing import Any

from analytics.ports import AnalyticsDataSource, AnalyticsRecord
from insights.models import InsightRun
from insights.repository import InsightRepository
from insights.schemas import (
    InsightRead,
    InsightRequest,
    InsightResult,
    InsightRunPage,
    InsightRunSummary,
    InsightSeverity,
    InsightType,
)


class InsightDataUnavailableError(LookupError):
    pass


RECOMMENDATIONS = {
    "visibility": "Review weak visibility drivers and execute the highest-priority action plan.",
    "mention": "Increase high-quality, independently verifiable brand mentions.",
    "recommendation": "Strengthen trust and relevance signals that drive model recommendations.",
    "citation": "Add authoritative, crawlable sources with clear attribution.",
    "coverage": "Expand presence across additional sources, models, and markets.",
    "confidence": "Improve entity consistency, structured facts, and source agreement.",
}


class InsightService:
    ENGINE_VERSION = "1.0"

    def __init__(self, source: AnalyticsDataSource, repository: InsightRepository) -> None:
        self.source = source
        self.repository = repository

    def generate(self, request: InsightRequest) -> InsightResult:
        records = self.source.records(request.date_from, request.date_to)
        selected = set(request.entity_ids)
        grouped: dict[str, list[AnalyticsRecord]] = defaultdict(list)
        for record in records:
            entity_id = record.dimensions.get("entity_id", "")
            if entity_id and (not selected or entity_id in selected):
                grouped[entity_id].append(record)
        if not grouped:
            raise InsightDataUnavailableError("No insight observations match the request")
        for observations in grouped.values():
            observations.sort(key=lambda item: item.observed_at)
        candidates: list[dict[str, Any]] = []
        recommendations: set[tuple[str, str]] = set()
        for entity_id, observations in sorted(grouped.items()):
            for metric in request.metrics:
                series = [item.metrics[metric] for item in observations if metric in item.metrics]
                if not series:
                    continue
                current = series[-1]
                if len(series) >= 2:
                    previous = series[0]
                    change = current - previous
                    percentage = self._percentage(previous, current)
                    if abs(percentage) >= request.change_threshold:
                        kind = InsightType.GROWTH if change > 0 else InsightType.DECLINE
                        severity = self._severity(abs(percentage), decline=change < 0)
                        candidates.append(
                            self._candidate(
                                kind,
                                severity,
                                entity_id,
                                metric,
                                f"{metric.title()} {'increased' if change > 0 else 'decreased'}",
                                (
                                    f"{metric.title()} changed by {percentage:.2f}% "
                                    "across the selected period."
                                ),
                                previous,
                                current,
                                change,
                                percentage,
                                min(1.0, len(series) / 5),
                                {"observation_count": len(series)},
                                RECOMMENDATIONS[metric] if change < 0 else None,
                            )
                        )
                        candidates.append(
                            self._candidate(
                                InsightType.KEY_CHANGE,
                                severity,
                                entity_id,
                                metric,
                                f"Key change in {metric}",
                                f"Absolute movement was {change:.2f} points.",
                                previous,
                                current,
                                change,
                                percentage,
                                min(1.0, len(series) / 5),
                                {"direction": "UP" if change > 0 else "DOWN"},
                            )
                        )
                        if change < 0:
                            recommendations.add((entity_id, metric))
                anomaly = self._anomaly(series, request.anomaly_z_threshold)
                if anomaly is not None:
                    candidates.append(
                        self._candidate(
                            InsightType.ANOMALY,
                            InsightSeverity.CRITICAL
                            if abs(anomaly) >= 3
                            else InsightSeverity.WARNING,
                            entity_id,
                            metric,
                            f"Anomalous {metric} value",
                            f"Latest value deviates from prior history by z={anomaly:.2f}.",
                            series[-2] if len(series) > 1 else None,
                            current,
                            None,
                            None,
                            min(1.0, abs(anomaly) / 3),
                            {"z_score": round(anomaly, 6), "history_size": len(series) - 1},
                            RECOMMENDATIONS[metric] if anomaly < 0 else None,
                        )
                    )
                    if anomaly < 0:
                        recommendations.add((entity_id, metric))
                if current < 50:
                    recommendations.add((entity_id, metric))
        candidates.extend(self._leaders(grouped, request))
        candidates.extend(self._recommendations(grouped, recommendations))
        candidates.sort(
            key=lambda item: (
                item["insight_type"],
                item.get("metric") or "",
                item.get("entity_id") or "",
                item["title"],
            )
        )
        return self._read(
            self.repository.create(request, sum(map(len, grouped.values())), candidates)
        )

    def get(self, run_id: int) -> InsightResult:
        return self._read(self.repository.get(run_id))

    def list(self, page: int, page_size: int) -> InsightRunPage:
        rows, total = self.repository.list(page, page_size)
        return InsightRunPage(
            page=page,
            page_size=page_size,
            total=total,
            items=[
                InsightRunSummary(
                    id=row.id,
                    engine_version=row.engine_version,
                    source_record_count=row.source_record_count,
                    insight_count=row.insight_count,
                    calculated_at=row.calculated_at,
                )
                for row in rows
            ],
        )

    @staticmethod
    def _leaders(
        grouped: dict[str, list[AnalyticsRecord]], request: InsightRequest
    ) -> list[dict[str, Any]]:
        result = []
        for metric in request.metrics:
            latest = {
                entity: next(
                    (item.metrics[metric] for item in reversed(records) if metric in item.metrics),
                    None,
                )
                for entity, records in grouped.items()
            }
            ranked = sorted(
                ((entity, value) for entity, value in latest.items() if value is not None),
                key=lambda item: (-item[1], item[0]),
            )[: request.leader_count]
            for rank, (entity, value) in enumerate(ranked, start=1):
                result.append(
                    InsightService._candidate(
                        InsightType.LEADER,
                        InsightSeverity.INFO,
                        entity,
                        metric,
                        f"{metric.title()} leader #{rank}",
                        f"Entity ranks #{rank} with {value:.2f} points.",
                        None,
                        value,
                        None,
                        None,
                        1.0,
                        {"rank": rank, "population_size": len(latest)},
                    )
                )
        return result

    @staticmethod
    def _recommendations(
        grouped: dict[str, list[AnalyticsRecord]], keys: set[tuple[str, str]]
    ) -> list[dict[str, Any]]:
        result = []
        for entity, metric in sorted(keys):
            current = next(
                item.metrics[metric] for item in reversed(grouped[entity]) if metric in item.metrics
            )
            result.append(
                InsightService._candidate(
                    InsightType.RECOMMENDATION,
                    InsightSeverity.WARNING if current >= 30 else InsightSeverity.CRITICAL,
                    entity,
                    metric,
                    f"Improve {metric}",
                    RECOMMENDATIONS[metric],
                    None,
                    current,
                    None,
                    None,
                    0.9,
                    {"rule": "decline-anomaly-or-low-score", "threshold": 50},
                    RECOMMENDATIONS[metric],
                )
            )
        return result

    @staticmethod
    def _anomaly(values: list[float], threshold: float) -> float | None:
        if len(values) < 3:
            return None
        history = values[:-1]
        average = sum(history) / len(history)
        deviation = sqrt(sum((value - average) ** 2 for value in history) / len(history))
        if deviation == 0:
            z_score = 10.0 if values[-1] > average else -10.0 if values[-1] < average else 0.0
        else:
            z_score = (values[-1] - average) / deviation
        return z_score if abs(z_score) >= threshold else None

    @staticmethod
    def _percentage(previous: float, current: float) -> float:
        if previous == 0:
            return 0.0 if current == 0 else 100.0 if current > 0 else -100.0
        return round((current - previous) / abs(previous) * 100, 6)

    @staticmethod
    def _severity(change: float, *, decline: bool) -> InsightSeverity:
        if decline and change >= 20:
            return InsightSeverity.CRITICAL
        return InsightSeverity.WARNING if decline or change >= 20 else InsightSeverity.INFO

    @staticmethod
    def _candidate(
        kind: InsightType,
        severity: InsightSeverity,
        entity_id: str | None,
        metric: str | None,
        title: str,
        description: str,
        previous_value: float | None,
        current_value: float | None,
        absolute_change: float | None,
        percentage_change: float | None,
        confidence: float,
        evidence: dict[str, object],
        recommendation: str | None = None,
    ) -> dict[str, Any]:
        return {
            "insight_type": kind.value,
            "severity": severity.value,
            "entity_id": entity_id,
            "metric": metric,
            "title": title,
            "description": description,
            "previous_value": previous_value,
            "current_value": current_value,
            "absolute_change": absolute_change,
            "percentage_change": percentage_change,
            "confidence": round(confidence, 6),
            "evidence": evidence,
            "recommendation": recommendation,
        }

    @staticmethod
    def _read(run: InsightRun) -> InsightResult:
        return InsightResult(
            id=run.id,
            engine_version=run.engine_version,
            source_record_count=run.source_record_count,
            insight_count=run.insight_count,
            calculated_at=run.calculated_at,
            request=InsightRequest.model_validate(run.request_payload),
            insights=[
                InsightRead(
                    id=item.id,
                    insight_type=InsightType(item.insight_type),
                    severity=InsightSeverity(item.severity),
                    entity_id=item.entity_id,
                    metric=item.metric,
                    title=item.title,
                    description=item.description,
                    previous_value=item.previous_value,
                    current_value=item.current_value,
                    absolute_change=item.absolute_change,
                    percentage_change=item.percentage_change,
                    confidence=item.confidence,
                    evidence=item.evidence,
                    recommendation=item.recommendation,
                )
                for item in sorted(run.insights, key=lambda value: value.id)
            ],
        )
