from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.orm import Session

from alice_learning.adapters import ResearchOrganizationSource
from alice_learning.automation_ports import (
    AutomationLaunchRequest,
    AutomationLaunchResult,
    AutomationTemplateContext,
)
from alice_learning.integration import learn_from_completed_research
from competitor_intelligence.service import CompetitorIntelligenceService
from notification_center.repository import NotificationRepository
from notification_center.service import NotificationService
from product.service import ProductPipeline
from research.models import Research, ResearchStatus
from research.repositories import ResearchRepository
from research.schemas import (
    ResearchCreate,
    ResearchModelSelection,
    ResearchRunRequest,
)
from research.service import run_research
from yandex_intelligence.service import YandexIntelligenceQuerySource


class ProductAutomationResearchAdapter:
    def __init__(self, db: Session) -> None:
        self.db = db

    def launch(self, request: AutomationLaunchRequest) -> AutomationLaunchResult:
        template = self.db.get(Research, request.template_research_id)
        if template is None:
            raise LookupError("Шаблон исследования не найден")
        queries = [
            {
                "id": str(uuid5(NAMESPACE_URL, f"alice-auto:{template.id}:{index}:{text}")),
                "cluster": "alice_automated_monitoring",
                "intent": "recommendation",
                "text": text,
                "repetition": str(index),
                "frozen_text": "true",
            }
            for index, text in enumerate(request.queries)
        ]
        research = ResearchRepository(self.db).create(
            ResearchCreate(
                entity_id=template.entity_id,
                project_id=template.project_id,
                domain_id=template.domain_id,
                title=f"Автомониторинг Алисы: {request.brand}",
                description=template.description,
                objective=template.objective,
                metadata={
                    **template.metadata_payload,
                    "brand": request.brand,
                    "website_url": request.website_url,
                    "languages": [request.language],
                    "regions": [request.region],
                    "research_profile": request.research_profile,
                    "routing_profile": request.routing_profile,
                    "query_catalog": queries,
                    "automated": True,
                    "template_research_id": template.id,
                },
            )
        )
        pipeline = ProductPipeline(
            self.db,
            notifications=NotificationService(NotificationRepository(self.db)),
            user_id=request.owner_user_id,
        )
        pipeline.ensure_research_runner()
        result = run_research(
            self.db,
            research.id,
            ResearchRunRequest(
                models=[ResearchModelSelection.model_validate(item) for item in request.models],
                routing_profile=request.routing_profile,
                queries=queries,
            ),
        )
        if result.status == ResearchStatus.COMPLETED:
            pipeline.complete_existing(result)
            CompetitorIntelligenceService(self.db).ingest_research(result.id)
            learned = learn_from_completed_research(self.db, result.id)
        else:
            learned = 0
        self.db.refresh(result)
        responses = [response for task in result.tasks for response in task.responses]
        actual_cost = round(sum(float(item.cost or 0) for item in responses), 8)
        return AutomationLaunchResult(
            research_id=result.id,
            succeeded=result.status == ResearchStatus.COMPLETED,
            actual_cost_usd=actual_cost,
            result={
                "responses": len(responses),
                "completed_tasks": result.completed_tasks,
                "failed_tasks": result.failed_tasks,
                "query_map_version": result.metadata_payload.get("query_map_version"),
                "alice_observations": learned,
            },
            error=None
            if result.status == ResearchStatus.COMPLETED
            else "Исследование завершилось с ошибкой",
        )


class ResearchAutomationTemplateAdapter:
    def __init__(self, db: Session) -> None:
        self.db = db

    def context(
        self, organization_id: int, template_research_id: int, website_url: str
    ) -> AutomationTemplateContext:
        template = self.db.get(Research, template_research_id)
        if template is None:
            raise LookupError("Шаблон исследования не найден")
        resolved = ResearchOrganizationSource(self.db).organization_id(template.id)
        if resolved is not None and resolved != organization_id:
            raise PermissionError("Нет доступа к шаблону исследования")
        queries = list(template.metadata_payload.get("query_catalog", []))
        snapshot_id, observed = YandexIntelligenceQuerySource(self.db).queries(
            organization_id, website_url, limit=12
        )
        seen = {str(item.get("text", "")).casefold() for item in queries}
        for index, text in enumerate(observed):
            if text.casefold() not in seen:
                queries.append(
                    {
                        "id": str(uuid5(NAMESPACE_URL, f"alice-auto-yandex:{snapshot_id}:{text}")),
                        "cluster": "yandex_webmaster_observed",
                        "intent": "observed_search_demand",
                        "text": text,
                        "source_rank": str(index + 1),
                    }
                )
        if not queries:
            raise ValueError("В исследовании нет карты запросов; сначала запустите Research Wizard")
        return AutomationTemplateContext(
            queries=tuple(queries),
            metadata={
                "template_research_id": template.id,
                "query_map_version": template.metadata_payload.get("query_map_version"),
                "yandex_snapshot_id": snapshot_id or None,
            },
        )


def build_alice_automation_service(db: Session):
    from alice_learning.automation_repository import AliceAutomationRepository
    from alice_learning.automation_service import AliceAutomationService

    return AliceAutomationService(
        AliceAutomationRepository(db),
        ProductAutomationResearchAdapter(db),
        ResearchAutomationTemplateAdapter(db),
        NotificationService(NotificationRepository(db)),
    )
