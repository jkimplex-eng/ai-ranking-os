from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from publication_learning.models import PublicationExperiment, PublicationInfluenceEstimate
from publication_learning.repository import PublicationLearningRepository
from research.models import (
    Research,
    ResearchScore,
    ResearchStatus,
    ResearchTask,
    Response,
    ResponseProcessingStatus,
)
from research.scoring import response_recommends_target
from research_lab.models import ResearchPublication
from research_lab.repository import PublicationRepository
from research_lab.schemas import ObservationCreate

ALGORITHM_VERSION = "1.2"
METRICS = (
    "visibility_score",
    "mention_score",
    "recommendation_score",
    "citation_score",
    "coverage_score",
    "confidence_score",
)


class PublicationLearningService:
    """Learn reproducible publication effects from matched longitudinal research."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = PublicationLearningRepository(db)

    def evaluate_followup(self, research_id: int) -> list[PublicationExperiment]:
        followup = self._research(research_id)
        if followup.entity_id is None:
            return []
        publications = list(
            self.db.scalars(
                select(ResearchPublication)
                .options(selectinload(ResearchPublication.observations))
                .where(
                    ResearchPublication.entity_id == followup.entity_id,
                    ResearchPublication.published_at <= followup.created_at,
                )
                .order_by(ResearchPublication.published_at)
            )
        )
        saved: list[PublicationExperiment] = []
        for publication in publications:
            detection_response_ids = self._record_observations(publication, followup)
            baseline = self._matched_baseline(followup, publication)
            if baseline is None:
                continue
            if self._score(baseline.id).version != self._score(followup.id).version:
                continue
            existing = self.db.scalar(
                select(PublicationExperiment).where(
                    PublicationExperiment.publication_id == publication.id,
                    PublicationExperiment.followup_research_id == followup.id,
                    PublicationExperiment.algorithm_version == ALGORITHM_VERSION,
                )
            )
            if existing is None:
                existing = self._build_experiment(
                    publication, baseline, followup, detection_response_ids
                )
                self.db.add(existing)
            else:
                refreshed = self._build_experiment(
                    publication, baseline, followup, detection_response_ids
                )
                for key in (
                    "baseline_research_id",
                    "matrix_fingerprint",
                    "status",
                    "causality_status",
                    "evidence_grade",
                    "evidence_level",
                    "metric_deltas",
                    "provider_deltas",
                    "sample_size",
                    "baseline_sample_size",
                    "followup_sample_size",
                    "matched_pairs",
                    "failed_responses",
                    "confidence_score",
                    "confidence_method",
                    "evidence_matrix",
                    "design_type",
                    "treatment_pairs",
                    "control_pairs",
                    "adjusted_metric_deltas",
                    "effect_method",
                    "limitations",
                    "evaluated_at",
                ):
                    setattr(existing, key, getattr(refreshed, key))
            saved.append(existing)
        self.db.commit()
        if saved:
            self._rebuild_estimates()
        return saved

    def _record_observations(
        self, publication: ResearchPublication, followup: Research
    ) -> list[int]:
        responses = list(
            self.db.scalars(
                select(Response)
                .join(ResearchTask)
                .where(ResearchTask.research_id == followup.id)
                .order_by(Response.finished_at, Response.id)
            )
        )
        needle = publication.url.rstrip("/").casefold()
        recorded = False
        response_ids: list[int] = []
        for response in responses:
            haystack = "\n".join(
                (
                    response.content,
                    json.dumps(response.normalized_response, ensure_ascii=False),
                )
            )
            index = haystack.casefold().find(needle)
            if index < 0:
                continue
            response_ids.append(response.id)
            start, end = max(0, index - 160), min(len(haystack), index + len(needle) + 160)
            PublicationRepository(self.db).record_observation(
                publication.id,
                ObservationCreate(
                    research_id=followup.id,
                    response_id=response.id,
                    provider=response.provider,
                    model=response.model,
                    first_observed_at=response.finished_at,
                    evidence_excerpt=haystack[start:end],
                ),
            )
            recorded = True
        if recorded:
            self.db.refresh(publication, ["observations"])
        return response_ids

    def summary(self, entity_id: UUID) -> dict[str, Any]:
        experiments = self.repository.experiments_for_entity(entity_id)
        domains = {
            self._domain(self.db.get(ResearchPublication, item.publication_id).url)
            for item in experiments
            if self.db.get(ResearchPublication, item.publication_id) is not None
        }
        estimates = [
            item
            for item in self.repository.estimates({"algorithm_version": ALGORITHM_VERSION})
            if item.resource_domain in domains
        ]
        return {
            "entity_id": entity_id,
            "experiments": experiments,
            "influence_estimates": estimates,
            "status": "LEARNING" if experiments else "INSUFFICIENT_DATA",
            "explanation": (
                "Оценки основаны на одинаковых матрицах запросов до и после публикаций. "
                "Причинность считается подтверждённой только после повторяемых "
                "контролируемых наблюдений."
                if experiments
                else "Добавьте публикацию и повторите идентичное исследование после её выхода."
            ),
        }

    def _matched_baseline(
        self, followup: Research, publication: ResearchPublication
    ) -> Research | None:
        candidates = list(
            self.db.scalars(
                select(Research)
                .options(selectinload(Research.tasks))
                .where(
                    Research.entity_id == followup.entity_id,
                    Research.created_at < publication.published_at,
                    Research.status == ResearchStatus.COMPLETED,
                )
                .order_by(Research.created_at.desc())
            )
        )
        fingerprint = self._matrix_fingerprint(followup)
        return next(
            (item for item in candidates if self._matrix_fingerprint(item) == fingerprint), None
        )

    def _build_experiment(
        self,
        publication: ResearchPublication,
        baseline: Research,
        followup: Research,
        detection_response_ids: list[int],
    ) -> PublicationExperiment:
        before = self._score(baseline.id)
        after = self._score(followup.id)
        metric_deltas = {
            metric: round(float(getattr(after, metric)) - float(getattr(before, metric)), 4)
            for metric in METRICS
        }
        baseline_providers = self._provider_signals(baseline)
        followup_providers = self._provider_signals(followup)
        provider_deltas = {
            key: {
                metric: round(followup_providers[key][metric] - baseline_providers[key][metric], 4)
                for metric in ("mention_score", "recommendation_score", "citation_score")
            }
            for key in sorted(set(baseline_providers) & set(followup_providers))
        }
        observed = bool(detection_response_ids)
        evidence_matrix = self._evidence_matrix(baseline, followup)
        evidence_matrix["publication_detection"] = {
            "url": publication.url,
            "detected": observed,
            "followup_response_ids": detection_response_ids,
        }
        baseline_size = len(evidence_matrix["baseline"])
        followup_size = len(evidence_matrix["followup"])
        matched_pairs = sum(pair["eligible"] for pair in evidence_matrix["pairs"])
        target_queries = {
            self._normalize_query(query) for query in publication.target_queries if query.strip()
        }
        eligible_pairs = [pair for pair in evidence_matrix["pairs"] if pair["eligible"]]
        treatment = [
            pair
            for pair in eligible_pairs
            if self._normalize_query(pair["query"]) in target_queries
        ]
        controls = [
            pair
            for pair in eligible_pairs
            if self._normalize_query(pair["query"]) not in target_queries
        ]
        adjusted_deltas = self._difference_in_differences(treatment, controls)
        controlled = bool(treatment and controls)
        controlled_provider_deltas = self._provider_difference_in_differences(
            treatment, controls
        )
        provider_deltas.update(controlled_provider_deltas)
        evidence_matrix["controlled_provider_keys"] = sorted(controlled_provider_deltas)
        failed_responses = sum(
            bool(row["excluded"])
            for phase in ("baseline", "followup")
            for row in evidence_matrix[phase]
        )
        eligible = max(baseline_size, followup_size, 1)
        coverage = matched_pairs / eligible
        confidence = min(0.95, coverage * (0.45 + min(matched_pairs, 20) / 40))
        if not observed:
            confidence *= 0.35
        confidence = round(confidence, 4)
        evidence_level = (
            "CONTROLLED" if observed and controlled else "OBSERVATION" if observed else "HYPOTHESIS"
        )
        evidence_grade = (
            "MODERATE" if observed and matched_pairs >= 8 and coverage >= 0.8 else "PRELIMINARY"
        )
        limitations = [
            "Совпадение до/после показывает ассоциацию, но не доказывает причинность.",
            "Внутренние механизмы поиска и ранжирования ИИ недоступны для проверки.",
        ]
        if not observed:
            limitations.insert(
                0,
                "URL публикации не обнаружен в ответах; изменение метрик не обучает площадку.",
            )
        if not treatment:
            limitations.append(
                "Целевые запросы публикации не совпали с матрицей исследования; "
                "эффект не скорректирован."
            )
        elif not controls:
            limitations.append(
                "Контрольных запросов нет; показано изменение до/после без поправки "
                "на общий дрейф модели."
            )
        if failed_responses:
            limitations.append(
                f"Исключено неуспешных или отсутствующих ответов: {failed_responses}."
            )
        return PublicationExperiment(
            publication_id=publication.id,
            entity_id=followup.entity_id,
            baseline_research_id=baseline.id,
            followup_research_id=followup.id,
            matrix_fingerprint=self._matrix_fingerprint(followup),
            status="MATCHED",
            causality_status=(
                "CONTROLLED_ASSOCIATION"
                if observed and controlled
                else "OBSERVED_ASSOCIATION"
                if observed
                else "UNVERIFIED_TIMING_ASSOCIATION"
            ),
            evidence_grade=evidence_grade,
            evidence_level=evidence_level,
            metric_deltas=metric_deltas,
            provider_deltas=provider_deltas,
            sample_size=matched_pairs,
            baseline_sample_size=baseline_size,
            followup_sample_size=followup_size,
            matched_pairs=matched_pairs,
            failed_responses=failed_responses,
            confidence_score=confidence,
            confidence_method="MATCHED_RESPONSE_COVERAGE_V1",
            evidence_matrix=evidence_matrix,
            design_type=(
                "MATCHED_DIFFERENCE_IN_DIFFERENCES"
                if controlled
                else "MATCHED_BEFORE_AFTER"
            ),
            treatment_pairs=len(treatment),
            control_pairs=len(controls),
            adjusted_metric_deltas=adjusted_deltas,
            effect_method=(
                "QUERY_LEVEL_DIFFERENCE_IN_DIFFERENCES_V1"
                if controlled
                else "RAW_BEFORE_AFTER_V1"
            ),
            limitations=limitations,
            algorithm_version=ALGORITHM_VERSION,
            evaluated_at=datetime.now(UTC),
        )

    def _rebuild_estimates(self) -> None:
        experiments = list(
            self.db.scalars(
                select(PublicationExperiment).where(
                    PublicationExperiment.algorithm_version == ALGORITHM_VERSION,
                    PublicationExperiment.evidence_level != "HYPOTHESIS",
                )
            )
        )
        grouped: defaultdict[
            tuple[str, ...], list[tuple[float, datetime, float, bool]]
        ] = defaultdict(list)
        for experiment in experiments:
            publication = self.db.get(ResearchPublication, experiment.publication_id)
            followup = self.db.get(Research, experiment.followup_research_id)
            if publication is None or followup is None:
                continue
            dimensions = (
                self._domain(publication.url),
                publication.channel,
                publication.content_type,
                str(followup.metadata_payload.get("research_profile", "UNIVERSAL")),
                self._first(followup.metadata_payload, "languages", "language", "ALL"),
                self._first(followup.metadata_payload, "regions", "region", "ALL"),
            )
            learned_deltas = dict(experiment.metric_deltas)
            learned_deltas.update(experiment.adjusted_metric_deltas or {})
            is_controlled = experiment.effect_method == "QUERY_LEVEL_DIFFERENCE_IN_DIFFERENCES_V1"
            for metric, delta in learned_deltas.items():
                grouped[(*dimensions, metric, "ALL", "ALL")].append(
                    (
                        float(delta),
                        experiment.evaluated_at,
                        experiment.confidence_score,
                        is_controlled,
                    )
                )
            for provider_model, deltas in experiment.provider_deltas.items():
                provider, _, model = provider_model.partition("/")
                provider_is_controlled = provider_model in set(
                    experiment.evidence_matrix.get("controlled_provider_keys", [])
                )
                for metric, delta in deltas.items():
                    grouped[(*dimensions, metric, provider, model or "ALL")].append(
                        (
                            float(delta),
                            experiment.evaluated_at,
                            experiment.confidence_score,
                            provider_is_controlled,
                        )
                    )

        self.db.execute(
            delete(PublicationInfluenceEstimate).where(
                PublicationInfluenceEstimate.algorithm_version == ALGORITHM_VERSION
            )
        )
        now = datetime.now(UTC)
        for key, observations in grouped.items():
            domain, channel, content_type, category, language, region, metric, provider, model = key
            values = [item[0] for item in observations]
            expected = statistics.fmean(values)
            spread = statistics.stdev(values) if len(values) > 1 else 30.0
            margin = self._critical_value(len(values)) * spread / math.sqrt(len(values))
            confidence = min(
                0.95,
                statistics.fmean(item[2] for item in observations)
                * (0.65 + min(len(values), 5) * 0.07),
            )
            grade = (
                "STRONG" if len(values) >= 5 else "MODERATE" if len(values) >= 3 else "PRELIMINARY"
            )
            evidence_level = "CORRELATION" if len(values) >= 3 else "OBSERVATION"
            positive = sum(value > 1 for value in values)
            negative = sum(value < -1 for value in values)
            neutral = len(values) - positive - negative
            controlled_count = sum(item[3] for item in observations)
            self.db.add(
                PublicationInfluenceEstimate(
                    resource_domain=domain,
                    channel=channel,
                    content_type=content_type,
                    metric=metric,
                    provider=provider,
                    model=model,
                    category=category,
                    language=language,
                    region=region,
                    sample_size=len(values),
                    expected_delta=round(expected, 4),
                    confidence_min=round(max(-100.0, expected - margin), 4),
                    confidence_max=round(min(100.0, expected + margin), 4),
                    confidence_score=round(confidence, 4),
                    evidence_grade=grade,
                    evidence_level=evidence_level,
                    positive_experiments=positive,
                    negative_experiments=negative,
                    neutral_experiments=neutral,
                    controlled_experiments=controlled_count,
                    effect_method=(
                        "QUERY_LEVEL_DIFFERENCE_IN_DIFFERENCES_V1"
                        if controlled_count == len(observations)
                        else "MIXED_EVIDENCE_V1"
                    ),
                    last_observed_at=max(item[1] for item in observations),
                    limitations=[
                        "Оценка отражает наблюдаемую связь, а не гарантированный причинный эффект.",
                        "Диапазон расширяется при малом числе сопоставимых экспериментов.",
                        f"Контролируемых наблюдений: {controlled_count} из {len(observations)}.",
                    ],
                    algorithm_version=ALGORITHM_VERSION,
                    updated_at=now,
                )
            )
        self.db.commit()

    def _evidence_matrix(self, baseline: Research, followup: Research) -> dict[str, Any]:
        before = self._evidence_rows(baseline)
        after = self._evidence_rows(followup)
        before_by_key: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        after_by_key: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in before:
            before_by_key[row["stable_key"]].append(row)
        for row in after:
            after_by_key[row["stable_key"]].append(row)
        pairs: list[dict[str, Any]] = []
        for key in sorted(set(before_by_key) & set(after_by_key)):
            for left, right in zip(before_by_key[key], after_by_key[key], strict=False):
                pairs.append(
                    {
                        "stable_key": key,
                        "query": left["query"],
                        "provider": left["provider"],
                        "model": left["model"],
                        "baseline_response_id": left["response_id"],
                        "followup_response_id": right["response_id"],
                        "eligible": not left["excluded"] and not right["excluded"],
                        "signal_delta": {
                            signal: int(right[signal]) - int(left[signal])
                            for signal in ("mentioned", "recommended", "cited")
                        },
                    }
                )
        return {"baseline": before, "followup": after, "pairs": pairs}

    @staticmethod
    def _difference_in_differences(
        treatment: list[dict[str, Any]], controls: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Estimate query-level effect while subtracting model-wide drift.

        Only response-derived metrics are adjusted. The aggregate visibility score remains
        available as the raw before/after delta because its weighted formula cannot be
        reconstructed from a subset of queries without changing the scoring contract.
        """
        if not treatment or not controls:
            return {}
        metric_signals = {
            "mention_score": "mentioned",
            "recommendation_score": "recommended",
            "citation_score": "cited",
        }
        result: dict[str, float] = {}
        for metric, signal in metric_signals.items():
            treatment_delta = statistics.fmean(
                pair["signal_delta"][signal] * 100 for pair in treatment
            )
            control_delta = statistics.fmean(
                pair["signal_delta"][signal] * 100 for pair in controls
            )
            result[metric] = round(treatment_delta - control_delta, 4)
        return result

    @classmethod
    def _provider_difference_in_differences(
        cls,
        treatment: list[dict[str, Any]],
        controls: list[dict[str, Any]],
    ) -> dict[str, dict[str, float]]:
        treatment_by_provider: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        controls_by_provider: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for pair in treatment:
            key = f"{pair['provider']}/{pair['model']}"
            treatment_by_provider[key].append(pair)
        for pair in controls:
            key = f"{pair['provider']}/{pair['model']}"
            controls_by_provider[key].append(pair)
        return {
            key: cls._difference_in_differences(
                treatment_by_provider[key], controls_by_provider[key]
            )
            for key in sorted(set(treatment_by_provider) & set(controls_by_provider))
        }

    def _evidence_rows(self, research: Research) -> list[dict[str, Any]]:
        target = str(research.metadata_payload.get("target_entity", research.title)).casefold()
        tasks = list(
            self.db.scalars(
                select(ResearchTask)
                .where(ResearchTask.research_id == research.id)
                .options(
                    selectinload(ResearchTask.responses).selectinload(
                        Response.extracted_citations
                    ),
                    selectinload(ResearchTask.responses).selectinload(
                        Response.extracted_recommendations
                    ),
                )
                .order_by(ResearchTask.id)
            )
        )
        rows: list[dict[str, Any]] = []
        for task in tasks:
            stable_key = self._response_key(task.query, task.provider, task.model)
            if not task.responses:
                rows.append(
                    {
                        "research_id": research.id,
                        "task_id": task.id,
                        "response_id": None,
                        "stable_key": stable_key,
                        "query": task.query,
                        "provider": task.provider or "",
                        "model": task.model or "",
                        "processing_status": "MISSING",
                        "mentioned": False,
                        "recommended": False,
                        "cited": False,
                        "citation_count": 0,
                        "excluded": True,
                        "exclusion_reason": task.error or "Ответ отсутствует",
                    }
                )
                continue
            for response in sorted(task.responses, key=lambda item: item.id):
                processed = response.processing_status == ResponseProcessingStatus.PROCESSED
                citations = response.extracted_citations or []
                normalized_citations = response.normalized_response.get("citations", [])
                citation_count = max(len(citations), len(normalized_citations))
                rows.append(
                    {
                        "research_id": research.id,
                        "task_id": task.id,
                        "response_id": response.id,
                        "stable_key": stable_key,
                        "query": task.query,
                        "provider": response.provider,
                        "model": response.model,
                        "processing_status": str(response.processing_status),
                        "mentioned": processed and target in response.content.casefold(),
                        "recommended": processed and response_recommends_target(response, target),
                        "cited": processed and citation_count > 0,
                        "citation_count": citation_count,
                        "excluded": not processed or bool(response.error_type),
                        "exclusion_reason": response.error_message or response.processing_error,
                    }
                )
        return rows

    def _provider_signals(self, research: Research) -> dict[str, dict[str, float]]:
        target = str(research.metadata_payload.get("target_entity", research.title)).casefold()
        responses = list(
            self.db.scalars(
                select(Response)
                .join(ResearchTask)
                .where(
                    ResearchTask.research_id == research.id,
                    Response.processing_status == ResponseProcessingStatus.PROCESSED,
                )
                .options(
                    selectinload(Response.extracted_entities),
                    selectinload(Response.extracted_citations),
                    selectinload(Response.extracted_recommendations),
                )
            )
        )
        grouped: defaultdict[str, list[Response]] = defaultdict(list)
        for response in responses:
            grouped[f"{response.provider}/{response.model}"].append(response)
        result: dict[str, dict[str, float]] = {}
        for key, items in grouped.items():
            denominator = len(items)
            result[key] = {
                "mention_score": self._ratio(
                    sum(target in item.content.casefold() for item in items), denominator
                ),
                "recommendation_score": self._ratio(
                    sum(response_recommends_target(item, target) for item in items), denominator
                ),
                "citation_score": self._ratio(
                    sum(bool(item.extracted_citations) for item in items), denominator
                ),
            }
        return result

    def _research(self, research_id: int) -> Research:
        item = self.db.scalar(
            select(Research).options(selectinload(Research.tasks)).where(Research.id == research_id)
        )
        if item is None:
            raise LookupError(f"Research {research_id} not found")
        return item

    def _score(self, research_id: int) -> ResearchScore:
        item = self.db.scalar(
            select(ResearchScore)
            .where(ResearchScore.research_id == research_id)
            .order_by(ResearchScore.calculated_at.desc())
        )
        if item is None:
            raise LookupError(f"Score for research {research_id} not found")
        return item

    @staticmethod
    def _matrix_fingerprint(research: Research) -> str:
        catalog = research.metadata_payload.get("query_catalog", [])
        queries = sorted(
            str(item.get("text", "")).strip().casefold()
            for item in catalog
            if isinstance(item, dict) and item.get("text")
        )
        if not queries:
            queries = sorted(task.query.strip().casefold() for task in research.tasks)
        models = sorted(
            f"{task.provider or ''}/{task.model or ''}".casefold() for task in research.tasks
        )
        payload = {
            "queries": queries,
            "models": models,
            "languages": research.metadata_payload.get("languages"),
            "regions": research.metadata_payload.get("regions"),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _response_key(query: str, provider: str | None, model: str | None) -> str:
        value = "|".join(
            (
                query.strip().casefold(),
                (provider or "").casefold(),
                (model or "").casefold(),
            )
        )
        return hashlib.sha256(value.encode()).hexdigest()[:24]

    @staticmethod
    def _normalize_query(query: str) -> str:
        return " ".join(query.casefold().split())

    @staticmethod
    def _critical_value(sample_size: int) -> float:
        if sample_size <= 1:
            return 1.0
        values = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447}
        return values.get(sample_size, 2.262 if sample_size < 30 else 1.96)

    @staticmethod
    def _domain(url: str) -> str:
        return (urlparse(url).hostname or "unknown").casefold()

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        return round(numerator / denominator * 100, 4) if denominator else 0.0

    @staticmethod
    def _first(metadata: dict[str, Any], plural: str, singular: str, default: str) -> str:
        value = metadata.get(plural, metadata.get(singular, default))
        return str(value[0] if isinstance(value, list) and value else value or default)
