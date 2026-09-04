from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from competitor_intelligence.models import (
    CompetitorDailySnapshot,
    CompetitorPublicationObservation,
)
from competitor_intelligence.repository import CompetitorIntelligenceRepository
from competitor_intelligence.schemas import (
    CompetitorAnalyticsRead,
    CompetitorDashboardRead,
    CompetitorPublicationRead,
    CompetitorSnapshotRead,
)
from project_monitoring.models import ProjectMonitor
from research.models import (
    ExtractedCitation,
    Research,
    ResearchStatus,
    ResearchTask,
    Response,
    ResponseProcessingStatus,
)
from workspace.models import ProjectCompetitor
from workspace.repository import CompetitorRepository, ProjectRepository, WorkspaceRepository


class CompetitorIntelligenceService:
    ALGORITHM_VERSION = "1.0"

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CompetitorIntelligenceRepository(db)

    def dashboard(self, user_id: int, project_id: int) -> CompetitorDashboardRead:
        self._authorize(user_id, project_id)
        monitor = self.db.scalar(
            select(ProjectMonitor).where(ProjectMonitor.project_id == project_id)
        )
        competitors = CompetitorRepository(self.db).list(project_id)
        return CompetitorDashboardRead(
            project_id=project_id,
            monitoring_enabled=bool(monitor and monitor.enabled),
            next_run_at=monitor.next_run_at if monitor and monitor.enabled else None,
            competitors=[self._analytics(item) for item in competitors],
        )

    def refresh_project(self, user_id: int, project_id: int) -> CompetitorDashboardRead:
        self._authorize(user_id, project_id)
        for research_id in self.db.scalars(
            select(Research.id).where(
                Research.project_id == project_id,
                Research.status == ResearchStatus.COMPLETED,
            )
        ):
            self.ingest_research(research_id)
        return self.dashboard(user_id, project_id)

    def ingest_research(self, research_id: int) -> None:
        research = self.db.scalar(
            select(Research)
            .where(Research.id == research_id, Research.status == ResearchStatus.COMPLETED)
            .options(
                selectinload(Research.tasks)
                .selectinload(ResearchTask.responses)
                .selectinload(Response.extracted_entities),
                selectinload(Research.tasks)
                .selectinload(ResearchTask.responses)
                .selectinload(Response.extracted_recommendations),
                selectinload(Research.tasks)
                .selectinload(ResearchTask.responses)
                .selectinload(Response.extracted_citations),
            )
        )
        if research is None or research.project_id is None:
            return
        competitors = [
            item for item in CompetitorRepository(self.db).list(research.project_id) if item.active
        ]
        if not competitors:
            return
        responses = [
            response
            for task in research.tasks
            for response in task.responses
            if response.processing_status == ResponseProcessingStatus.PROCESSED
            and not response.error_type
        ]
        day = research.created_at.date()
        for competitor in competitors:
            aliases = self._aliases(competitor)
            mentioned_responses = [r for r in responses if self._mentioned(r, aliases)]
            recommended_responses = [r for r in responses if self._recommended(r, aliases)]
            cited_urls: set[str] = set()
            for response in mentioned_responses:
                for citation in response.extracted_citations:
                    url = self._normalized_url(citation)
                    if not url:
                        continue
                    cited_urls.add(url)
                    if self.repository.observation_exists(competitor.id, response.id, url):
                        continue
                    self.repository.add_observation(
                        CompetitorPublicationObservation(
                            competitor_id=competitor.id,
                            research_id=research.id,
                            response_id=response.id,
                            url=url,
                            domain=(
                                urlparse(url).hostname or citation.source or "unknown"
                            ).casefold(),
                            title=citation.title,
                            provider=response.provider,
                            model=response.model,
                            mentioned=True,
                            recommended=response in recommended_responses,
                            first_seen_at=response.finished_at,
                            last_seen_at=response.finished_at,
                            excerpt=citation.excerpt,
                        )
                    )
            denominator = len(responses)
            mention_rate = self._rate(len(mentioned_responses), denominator)
            recommendation_rate = self._rate(len(recommended_responses), denominator)
            citation_rate = self._rate(
                sum(bool(r.extracted_citations) for r in mentioned_responses), denominator
            )
            observed_visibility = round(
                mention_rate * 0.50 + recommendation_rate * 0.35 + citation_rate * 0.15, 2
            )
            snapshot = self.repository.snapshot(competitor.id, day)
            if snapshot is None:
                snapshot = CompetitorDailySnapshot(competitor_id=competitor.id, snapshot_date=day)
            snapshot.research_count = 1
            snapshot.response_count = denominator
            snapshot.mention_count = len(mentioned_responses)
            snapshot.recommendation_count = len(recommended_responses)
            snapshot.citation_count = sum(len(r.extracted_citations) for r in mentioned_responses)
            snapshot.source_count = len(cited_urls)
            snapshot.observed_visibility_score = observed_visibility
            snapshot.evidence = {
                "research_ids": [research.id],
                "mention_rate": mention_rate,
                "recommendation_rate": recommendation_rate,
                "citation_association_rate": citation_rate,
                "formula": "0.50*mention + 0.35*recommendation + 0.15*citation_association",
                "causality": "OBSERVED_ASSOCIATION",
            }
            snapshot.algorithm_version = self.ALGORITHM_VERSION
            snapshot.calculated_at = datetime.now(UTC)
            self.repository.save_snapshot(snapshot)
        self.repository.commit()

    def _analytics(self, competitor: ProjectCompetitor) -> CompetitorAnalyticsRead:
        snapshots = list(reversed(self.repository.snapshots(competitor.id)))
        latest = snapshots[-1].observed_visibility_score if snapshots else None
        previous = snapshots[-2].observed_visibility_score if len(snapshots) > 1 else None
        return CompetitorAnalyticsRead(
            competitor_id=competitor.id,
            name=competitor.name,
            domains=competitor.domains,
            active=competitor.active,
            latest_visibility_score=latest,
            visibility_delta=(
                round(latest - previous, 2) if latest is not None and previous is not None else None
            ),
            snapshots=[
                CompetitorSnapshotRead.model_validate(item, from_attributes=True)
                for item in snapshots
            ],
            publications=self._publications(competitor.id),
        )

    def _publications(self, competitor_id: int) -> list[CompetitorPublicationRead]:
        groups: defaultdict[str, list[CompetitorPublicationObservation]] = defaultdict(list)
        for item in self.repository.observations(competitor_id):
            groups[item.url].append(item)
        result = []
        for url, items in groups.items():
            providers = {item.provider for item in items}
            researches = {item.research_id for item in items}
            recommendation_count = sum(item.recommended for item in items)
            recurrence = min(len(researches) / 5, 1.0)
            provider_coverage = min(len(providers) / 3, 1.0)
            recommendation_share = recommendation_count / len(items)
            score = round(
                (recurrence * 0.40 + provider_coverage * 0.30 + recommendation_share * 0.30) * 100,
                1,
            )
            label = "Высокая" if score >= 70 else "Средняя" if score >= 40 else "Предварительная"
            first = min(item.first_seen_at for item in items)
            last = max(item.last_seen_at for item in items)
            result.append(
                CompetitorPublicationRead(
                    url=url,
                    domain=items[0].domain,
                    title=items[0].title,
                    observation_count=len(items),
                    provider_count=len(providers),
                    research_count=len(researches),
                    mention_observations=len(items),
                    recommendation_observations=recommendation_count,
                    significance_score=score,
                    significance_label=label,
                    first_seen_at=first,
                    last_seen_at=last,
                    explanation=(
                        f"Источник встречался вместе с конкурентом в {len(items)} ответах, "
                        f"{len(researches)} исследованиях и у {len(providers)} провайдеров."
                    ),
                )
            )
        return sorted(result, key=lambda item: (-item.significance_score, item.domain))[:50]

    def _authorize(self, user_id: int, project_id: int) -> None:
        workspace = WorkspaceRepository(self.db).get_or_create(user_id)
        ProjectRepository(self.db).get(workspace.id, project_id)

    @staticmethod
    def _aliases(competitor: ProjectCompetitor) -> tuple[str, ...]:
        return tuple(
            {
                competitor.name.casefold(),
                *(value.casefold() for value in competitor.brands),
            }
        )

    @staticmethod
    def _mentioned(response: Response, aliases: tuple[str, ...]) -> bool:
        content = response.content.casefold()
        entities = {item.canonical_name.casefold() for item in response.extracted_entities}
        return any(alias in content or alias in entities for alias in aliases)

    @staticmethod
    def _recommended(response: Response, aliases: tuple[str, ...]) -> bool:
        return any(
            alias in item.content.casefold()
            for item in response.extracted_recommendations
            for alias in aliases
        )

    @staticmethod
    def _normalized_url(citation: ExtractedCitation) -> str:
        value = (citation.url or "").strip()
        return value if value.startswith(("http://", "https://")) else ""

    @staticmethod
    def _rate(count: int, total: int) -> float:
        return round(count / total * 100, 2) if total else 0.0
