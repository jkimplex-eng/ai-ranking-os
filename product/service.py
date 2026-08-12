from __future__ import annotations

from collections import defaultdict
from typing import Any
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.repository import SqlAlchemyAnalyticsRepository
from analytics.schemas import AnalyticsFilter, AnalyticsQuery, FilterOperator, Statistic
from analytics.service import AnalyticsService
from backend.app.analytics_source import PlatformAnalyticsDataSource
from backend.app.llm_router.ports import ProviderState
from backend.app.llm_router.registry import ModelRepository, RegistryNotFoundError, ensure_seeded
from backend.app.providers.readiness import RuntimeProviderReadiness
from benchmark.repository import SqlAlchemyBenchmarkRepository
from benchmark.schemas import BenchmarkRequest
from benchmark.service import BenchmarkService
from change_detection.ports import ChangeDetectorPort
from decision_center import service as decision_service
from decision_center.models import AgentType
from decision_center.schemas import AgentCreate
from graph.engine import GraphEngine
from graph.ports import (
    EntityProvider,
    GraphBuildContext,
    ProvidedEntity,
    ProvidedRelationship,
    RelationshipProvider,
)
from insights.repository import SqlAlchemyInsightRepository
from insights.schemas import InsightRequest
from insights.service import InsightService
from notification_center.ports import NotificationPort
from product.repository import ProductNotFoundError, PromptRepository, ResearchTemplateRepository
from product.schemas import WizardRequest, WizardReview
from provider_recommendation.research_adapter import SqlAlchemyResearchUsageSource
from provider_recommendation.service import SmartProviderRecommendationService
from recommendation.engine import RecommendationEngine
from recommendation.research_adapter import SqlAlchemyResearchScoreAdapter
from research.models import ExtractedEntity, Research, ResearchStatus, ResearchTask, Response
from research.reporting import ReportingService
from research.repositories import ResearchRepository
from research.schemas import ResearchCreate, ResearchRunRequest
from research.scoring import SCORING_VERSION, SCORING_WEIGHTS
from research.service import run_research
from trend.research_adapter import build_trend_engine


class WizardValidationError(ValueError):
    pass


PIPELINE = [
    "provider",
    "normalization",
    "extraction",
    "knowledge_graph",
    "scoring",
    "recommendations",
    "analytics",
    "insights",
    "report",
]


class PromptService:
    def __init__(self, db: Session) -> None:
        self.repository = PromptRepository(db)

    def render(self, code: str, language: str, values: dict[str, str]) -> str:
        prompt = self.repository.active(code, language)
        missing = [name for name in prompt.variables if not values.get(name)]
        if missing:
            raise WizardValidationError(f"Missing prompt variables: {', '.join(missing)}")
        try:
            return prompt.template.format_map(values)
        except KeyError as error:
            raise WizardValidationError(f"Missing prompt variable: {error.args[0]}") from error


class ResearchEntityProvider(EntityProvider, RelationshipProvider):
    """Public graph ports backed by persisted normalized Research extraction."""

    def __init__(self, db: Session, research_id: int) -> None:
        self.db = db
        self.research_id = research_id

    def entities(self, context: GraphBuildContext) -> list[ProvidedEntity]:
        rows = self.db.scalars(
            select(ExtractedEntity)
            .join(Response)
            .join(ResearchTask)
            .where(ResearchTask.research_id == self.research_id)
            .order_by(ExtractedEntity.id)
        ).all()
        return [
            ProvidedEntity(
                external_id=item.knowledge_graph_id or f"research-entity:{item.id}",
                name=item.name,
                canonical_name=item.canonical_name,
                node_type=item.entity_type.replace("_", " ").title().replace(" ", ""),
                confidence=item.confidence,
                aliases=tuple(item.aliases),
                metadata={"research_id": self.research_id, "response_id": item.response_id},
            )
            for item in rows
        ]

    def relationships(self, context: GraphBuildContext) -> list[ProvidedRelationship]:
        return []


class ProductPipeline:
    def __init__(
        self,
        db: Session,
        change_detector: ChangeDetectorPort | None = None,
        notifications: NotificationPort | None = None,
    ) -> None:
        self.db = db
        self.prompts = PromptService(db)
        self.templates = ResearchTemplateRepository(db)
        self.change_detector = change_detector
        self.notifications = notifications

    def review(self, payload: WizardRequest) -> WizardReview:
        template = self.templates.get(payload.research_template_code)
        values = self._values(payload)
        prompt = self.prompts.render(
            payload.prompt_code or template.prompt_code, payload.languages[0], values
        )
        selected = []
        estimated_cost = 0.0
        estimated_time = 0.0
        ensure_seeded(self.db)
        models = ModelRepository(self.db)
        for item in payload.models:
            try:
                model = models.get(item.model)
            except RegistryNotFoundError as error:
                raise WizardValidationError(
                    f"Модель {item.provider}/{item.model} не поддерживается"
                ) from error
            if model.provider != item.provider or "chat" not in model.capabilities:
                raise WizardValidationError(
                    f"Модель {item.model} не поддерживает текстовые запросы"
                )
            if RuntimeProviderReadiness(self.db).state(item.provider) != ProviderState.READY:
                raise WizardValidationError(
                    f"Провайдер {item.provider} сейчас не подключён. "
                    "Выберите модель со статусом «Подключена»."
                )
            selected.append(f"{item.provider}/{item.model}")
            prompt_tokens = max(1, len(prompt) // 4)
            estimated_cost += (
                prompt_tokens * model.pricing.input_per_million
                + 512 * model.pricing.output_per_million
            ) / 1_000_000
            estimated_time = max(estimated_time, model.latency_ms)
        if not selected:
            selected = [payload.routing_profile]
        return WizardReview(
            valid=True,
            title=f"{template.title}: {payload.brand}",
            prompt=prompt,
            provider_models=selected,
            languages=payload.languages,
            regions=payload.regions,
            pipeline=template.pipeline,
            estimated_cost_usd=round(estimated_cost, 8),
            estimated_time_ms=estimated_time,
            selected_models=selected,
        )

    def run(self, payload: WizardRequest) -> Research:
        review = self.review(payload)
        entity_id = payload.entity_id or uuid5(
            NAMESPACE_URL, f"ai-ranking-os:{payload.brand.casefold()}"
        )
        research = ResearchRepository(self.db).create(
            ResearchCreate(
                entity_id=entity_id,
                title=review.title,
                objective=review.prompt,
                metadata={
                    "brand": payload.brand,
                    "target_entity": payload.brand,
                    "languages": payload.languages,
                    "regions": payload.regions,
                    "prompt_code": payload.prompt_code,
                    "research_template_code": payload.research_template_code,
                    "research_scope": payload.research_scope,
                    "research_profile": payload.research_profile,
                    "routing_profile": payload.routing_profile,
                    "selected_models": [item.model_dump() for item in payload.models],
                    "pipeline": review.pipeline,
                },
            )
        )
        agents = decision_service.list_agents(self.db)
        if not any(
            agent.is_enabled
            and agent.agent_type == AgentType.CODEX
            and agent.specialization is None
            for agent in agents
        ):
            decision_service.create_agent(
                self.db,
                AgentCreate(name=f"product-research-runner-{len(agents) + 1}"),
            )
        research = run_research(
            self.db,
            research.id,
            ResearchRunRequest(
                models=payload.models,
                routing_profile=payload.routing_profile,
                query=review.prompt,
            ),
        )
        if research.status == ResearchStatus.COMPLETED:
            self._complete_product_pipeline(research)
        elif self.notifications is not None:
            self.notifications.emit(
                "RESEARCH_FAILED",
                "Ошибка исследования",
                f"Исследование {research.title} завершилось с ошибкой",
                resource_type="research",
                resource_id=str(research.id),
            )
        self.db.refresh(research)
        return research

    def _complete_product_pipeline(self, research: Research) -> None:
        artifacts: dict[str, Any] = {}
        recommendations = RecommendationEngine(
            self.db, SqlAlchemyResearchScoreAdapter(self.db)
        ).generate(research.id)
        artifacts["recommendations"] = recommendations.model_dump(mode="json")

        graph_provider = ResearchEntityProvider(self.db, research.id)
        graph = GraphEngine(self.db, graph_provider, graph_provider).build(
            GraphBuildContext(metadata={"research_id": research.id})
        )
        artifacts["knowledge_graph"] = graph.model_dump(mode="json")

        source = PlatformAnalyticsDataSource(self.db)
        entity = str(research.entity_id)
        analytics = AnalyticsService(source, SqlAlchemyAnalyticsRepository(self.db)).execute(
            AnalyticsQuery(
                metrics=[
                    "visibility",
                    "mention",
                    "recommendation",
                    "citation",
                    "coverage",
                    "confidence",
                ],
                group_by=["entity_id"],
                filters=[
                    AnalyticsFilter(field="entity_id", operator=FilterOperator.EQ, value=entity)
                ],
                statistics=[Statistic.AVG],
            )
        )
        artifacts["analytics"] = analytics.model_dump(mode="json")
        benchmark = BenchmarkService(source, SqlAlchemyBenchmarkRepository(self.db)).execute(
            BenchmarkRequest(entity_ids=[entity])
        )
        artifacts["benchmark"] = benchmark.model_dump(mode="json")
        insights = InsightService(source, SqlAlchemyInsightRepository(self.db)).generate(
            InsightRequest(entity_ids=[entity])
        )
        artifacts["insights"] = insights.model_dump(mode="json")
        trend = build_trend_engine(self.db).build(research.entity_id)
        artifacts["trend"] = trend.model_dump(mode="json")
        provider_advice = SmartProviderRecommendationService(
            self.db, SqlAlchemyResearchUsageSource(self.db)
        ).generate(research.id)
        artifacts["provider_recommendations"] = [
            item.model_dump(mode="json") for item in provider_advice
        ]
        research.metadata_payload = {**research.metadata_payload, "product_artifacts": artifacts}
        self.db.commit()
        if self.change_detector is not None:
            self.change_detector.detect(research.id)
        if self.notifications is not None:
            self.notifications.emit(
                "RESEARCH_COMPLETED",
                "Исследование завершено",
                f"Отчёт по исследованию {research.title} готов",
                resource_type="research",
                resource_id=str(research.id),
            )

    @staticmethod
    def _values(payload: WizardRequest) -> dict[str, str]:
        return {
            "brand": payload.brand,
            "language": ", ".join(payload.languages),
            "region": ", ".join(payload.regions),
            "research_profile": payload.research_profile,
            **payload.variables,
        }


class FinalReportService:
    """Read-only composition over persisted outputs from existing engines."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, research_id: int) -> dict[str, Any]:
        base = ReportingService(self.db).get_report(research_id)
        research = self.db.get(Research, research_id)
        if research is None:
            raise ProductNotFoundError(f"Research {research_id} not found")
        artifacts = research.metadata_payload.get("product_artifacts", {})
        responses = base.responses
        provider_stats: dict[str, dict[str, float | int]] = defaultdict(
            lambda: {"responses": 0, "latency_ms": 0, "tokens": 0, "cost": 0.0}
        )
        for response in responses:
            stats = provider_stats[response.provider]
            stats["responses"] += 1
            stats["latency_ms"] += response.latency_ms or 0
            stats["tokens"] += response.total_tokens
            stats["cost"] = round(float(stats["cost"]) + response.cost, 8)
        score = base.score.model_dump(mode="json") if base.score else None
        explainability = self._explainability(research, base, score)
        return {
            "executive_summary": self._summary(research, score),
            "research": base.research.model_dump(mode="json"),
            "score": score,
            "trend": artifacts.get("trend"),
            "benchmark": artifacts.get("benchmark"),
            "insights": artifacts.get("insights", {}).get("insights", []),
            "recommendations": artifacts.get("recommendations", {}).get("recommendations", []),
            "knowledge_graph_summary": artifacts.get("knowledge_graph"),
            "detected_entities": [item.model_dump(mode="json") for item in base.entities],
            "sources": [item.model_dump(mode="json") for item in base.citations],
            "responses": [item.model_dump(mode="json") for item in responses],
            "analytics": artifacts.get("analytics"),
            "provider_statistics": dict(provider_stats),
            "latency_ms": sum(item.latency_ms or 0 for item in responses),
            "token_usage": sum(item.total_tokens for item in responses),
            "cost": round(sum(item.cost for item in responses), 8),
            "execution_time_ms": sum(item.latency_ms or 0 for item in responses),
            "explainability": explainability,
        }

    @staticmethod
    def _explainability(
        research: Research, base: Any, score: dict[str, Any] | None
    ) -> dict[str, Any]:
        responses = base.responses
        target = next(
            (
                str(research.metadata_payload[key]).strip().casefold()
                for key in ("target_entity", "entity", "brand")
                if isinstance(research.metadata_payload.get(key), str)
                and str(research.metadata_payload[key]).strip()
            ),
            research.title.strip().casefold(),
        )
        entities_by_response: dict[int, list[Any]] = defaultdict(list)
        citations_by_response: dict[int, list[Any]] = defaultdict(list)
        recommendations_by_response: dict[int, list[Any]] = defaultdict(list)
        for entity in base.entities:
            entities_by_response[entity.response_id].append(entity)
        for citation in base.citations:
            citations_by_response[citation.response_id].append(citation)
        for recommendation in base.recommendations:
            recommendations_by_response[recommendation.response_id].append(recommendation)
        mentioned = sum(
            target in response.content.casefold()
            or any(
                target
                in {
                    entity.name.casefold(),
                    entity.canonical_name.casefold(),
                    *(alias.casefold() for alias in entity.aliases),
                }
                for entity in entities_by_response[response.id]
            )
            for response in responses
        )
        recommended = sum(bool(recommendations_by_response[response.id]) for response in responses)
        citation_count = len(base.citations)
        processed = sum(response.processing_status.value == "PROCESSED" for response in responses)
        unique_models = len(
            {
                (response.provider.casefold(), response.model.casefold())
                for response in responses
                if response.processing_status.value == "PROCESSED"
            }
        )
        expected = max(research.total_tasks, len(research.tasks), 1)
        metrics: dict[str, Any] = {
            "mention_score": {
                "formula": "mentioned_responses / total_responses * 100",
                "inputs": {"mentioned_responses": mentioned, "total_responses": len(responses)},
                "normalization": "bounded 0..100",
                "weight": SCORING_WEIGHTS["mention"],
            },
            "recommendation_score": {
                "formula": "responses_with_recommendations / total_responses * 100",
                "inputs": {
                    "responses_with_recommendations": recommended,
                    "total_responses": len(responses),
                },
                "normalization": "bounded 0..100",
                "weight": SCORING_WEIGHTS["recommendation"],
            },
            "citation_score": {
                "formula": "extracted_citations / (total_responses * 3) * 100",
                "inputs": {
                    "extracted_citations": citation_count,
                    "maximum_v1_citations": len(responses) * 3,
                },
                "normalization": "bounded 0..100",
                "weight": SCORING_WEIGHTS["citation"],
            },
            "coverage_score": {
                "formula": "unique_processed_provider_models / expected_tasks * 100",
                "inputs": {
                    "unique_processed_provider_models": unique_models,
                    "expected_tasks": expected,
                },
                "normalization": "bounded 0..100",
                "weight": SCORING_WEIGHTS["coverage"],
            },
            "confidence_score": {
                "formula": "processing_success * 70% + mean_entity_confidence * 30%",
                "inputs": {
                    "processed_responses": processed,
                    "total_responses": len(responses),
                    "entity_confidences": [entity.confidence for entity in base.entities],
                },
                "normalization": "bounded 0..100",
                "weight": SCORING_WEIGHTS["confidence"],
            },
            "visibility_score": {
                "formula": (
                    "mention*0.35 + recommendation*0.20 + citation*0.15 + "
                    "coverage*0.20 + confidence*0.10"
                ),
                "inputs": {
                    "research_id": research.id,
                    **(
                        {
                            key: score[key]
                            for key in (
                                "mention_score",
                                "recommendation_score",
                                "citation_score",
                                "coverage_score",
                                "confidence_score",
                            )
                        }
                        if score
                        else {}
                    ),
                },
                "normalization": "weighted sum bounded 0..100",
                "weight": 1.0,
            },
            "benchmark": {
                "formula": "population comparison; unavailable for fewer than two entities",
                "inputs": {},
                "normalization": "rank and percentile",
                "weight": None,
            },
            "authority": {
                "formula": None,
                "inputs": {},
                "normalization": None,
                "weight": None,
                "status": "NOT_CALCULATED_IN_SCORING_V1",
            },
            "knowledge_graph_score": {
                "formula": None,
                "inputs": {},
                "normalization": None,
                "weight": None,
                "status": "NOT_CALCULATED_IN_SCORING_V1",
            },
        }
        for payload in metrics.values():
            payload["version"] = score.get("version", SCORING_VERSION) if score else SCORING_VERSION
        prompts = [
            {
                "uuid": str(
                    uuid5(NAMESPACE_URL, f"research:{research.id}:response:{response.id}:prompt")
                ),
                "response_id": response.id,
                "text": response.prompt,
                "language": research.metadata_payload.get(
                    "languages", research.metadata_payload.get("language")
                ),
                "country": research.metadata_payload.get(
                    "regions", research.metadata_payload.get("region")
                ),
                "provider": response.provider,
                "model": response.model,
                "created_at": response.created_at,
            }
            for response in responses
        ]
        response_evidence = [
            {
                "response_id": response.id,
                "provider": response.provider,
                "model": response.model,
                "prompt": response.prompt,
                "raw_response": response.raw_response,
                "normalized_response": response.normalized_response,
                "tokens": response.total_tokens,
                "cost": response.cost,
                "latency_ms": response.latency_ms,
                "finished_at": response.finished_at,
                "error_type": response.error_type,
                "error_message": response.error_message,
                "entity_ids": [item.id for item in entities_by_response[response.id]],
                "citation_ids": [item.id for item in citations_by_response[response.id]],
                "recommendation_ids": [
                    item.id for item in recommendations_by_response[response.id]
                ],
            }
            for response in responses
        ]
        citation_evidence = [
            {
                "citation_id": citation.id,
                "response_id": citation.response_id,
                "url": citation.url,
                "domain": urlparse(citation.url).netloc.casefold() if citation.url else None,
                "source": citation.source,
                "title": citation.title,
                "position": citation.position,
            }
            for citation in base.citations
        ]
        return {
            "methodology_version": SCORING_VERSION,
            "metrics": metrics,
            "prompts": prompts,
            "responses": response_evidence,
            "citations": citation_evidence,
            "unsupported_metrics": ["authority", "knowledge_graph_score"],
        }

    @staticmethod
    def _summary(research: Research, score: dict[str, Any] | None) -> str:
        if not score:
            return f"Research {research.title} completed without a visibility score."
        return (
            f"{research.title} achieved AI Visibility {score['visibility_score']}/100 "
            f"using scoring algorithm {score['version']}."
        )
