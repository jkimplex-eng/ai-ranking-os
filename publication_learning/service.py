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

ALGORITHM_VERSION = "1.0"
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
            self._record_observations(publication, followup)
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
                existing = self._build_experiment(publication, baseline, followup)
                self.db.add(existing)
            else:
                refreshed = self._build_experiment(publication, baseline, followup)
                for key in (
                    "baseline_research_id",
                    "matrix_fingerprint",
                    "status",
                    "causality_status",
                    "evidence_grade",
                    "metric_deltas",
                    "provider_deltas",
                    "sample_size",
                    "evaluated_at",
                ):
                    setattr(existing, key, getattr(refreshed, key))
            saved.append(existing)
        self.db.commit()
        if saved:
            self._rebuild_estimates()
        return saved

    def _record_observations(self, publication: ResearchPublication, followup: Research) -> None:
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

    def summary(self, entity_id: UUID) -> dict[str, Any]:
        experiments = self.repository.experiments_for_entity(entity_id)
        domains = {
            self._domain(self.db.get(ResearchPublication, item.publication_id).url)
            for item in experiments
            if self.db.get(ResearchPublication, item.publication_id) is not None
        }
        estimates = [
            item for item in self.repository.estimates() if item.resource_domain in domains
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
        self, publication: ResearchPublication, baseline: Research, followup: Research
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
        observed = bool(publication.observations)
        sample_size = min(len(baseline.tasks), len(followup.tasks))
        evidence_grade = "MODERATE" if observed and sample_size >= 8 else "PRELIMINARY"
        return PublicationExperiment(
            publication_id=publication.id,
            entity_id=followup.entity_id,
            baseline_research_id=baseline.id,
            followup_research_id=followup.id,
            matrix_fingerprint=self._matrix_fingerprint(followup),
            status="MATCHED",
            causality_status="OBSERVED_ASSOCIATION",
            evidence_grade=evidence_grade,
            metric_deltas=metric_deltas,
            provider_deltas=provider_deltas,
            sample_size=sample_size,
            algorithm_version=ALGORITHM_VERSION,
            evaluated_at=datetime.now(UTC),
        )

    def _rebuild_estimates(self) -> None:
        experiments = list(self.db.scalars(select(PublicationExperiment)))
        grouped: defaultdict[tuple[str, ...], list[float]] = defaultdict(list)
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
            for metric, delta in experiment.metric_deltas.items():
                grouped[(*dimensions, metric, "ALL", "ALL")].append(float(delta))
            for provider_model, deltas in experiment.provider_deltas.items():
                provider, _, model = provider_model.partition("/")
                for metric, delta in deltas.items():
                    grouped[(*dimensions, metric, provider, model or "ALL")].append(float(delta))

        self.db.execute(delete(PublicationInfluenceEstimate))
        now = datetime.now(UTC)
        for key, values in grouped.items():
            domain, channel, content_type, category, language, region, metric, provider, model = key
            expected = statistics.fmean(values)
            spread = statistics.stdev(values) if len(values) > 1 else 20.0
            margin = 1.96 * spread / math.sqrt(len(values))
            confidence = min(0.95, 0.2 + len(values) * 0.12)
            grade = (
                "STRONG" if len(values) >= 5 else "MODERATE" if len(values) >= 3 else "PRELIMINARY"
            )
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
                    confidence_min=round(expected - margin, 4),
                    confidence_max=round(expected + margin, 4),
                    confidence_score=round(confidence, 4),
                    evidence_grade=grade,
                    algorithm_version=ALGORITHM_VERSION,
                    updated_at=now,
                )
            )
        self.db.commit()

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
    def _domain(url: str) -> str:
        return (urlparse(url).hostname or "unknown").casefold()

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        return round(numerator / denominator * 100, 4) if denominator else 0.0

    @staticmethod
    def _first(metadata: dict[str, Any], plural: str, singular: str, default: str) -> str:
        value = metadata.get(plural, metadata.get(singular, default))
        return str(value[0] if isinstance(value, list) and value else value or default)
