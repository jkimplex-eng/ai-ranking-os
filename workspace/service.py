from __future__ import annotations

from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from backend.app.llm_router.schemas import RoutingProfile
from research.ports import ResearchLaunchPort, ResearchLaunchRequest
from workspace.models import (
    BulkResearchItem,
    BulkResearchRun,
    Project,
    ProjectCompetitor,
    ProjectDomain,
    SavedResearchConfiguration,
)
from workspace.repository import (
    BulkResearchRepository,
    CompetitorRepository,
    DomainRepository,
    ProjectNotFoundError,
    ProjectRepository,
    SavedConfigurationRepository,
    WorkspaceRepository,
)
from workspace.schemas import (
    BulkResearchCreate,
    BulkResearchItemRead,
    BulkResearchRead,
    CompetitorCreate,
    CompetitorImport,
    CompetitorRead,
    CompetitorUpdate,
    DomainCreate,
    DomainImport,
    DomainRead,
    DomainUpdate,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    SavedConfigurationCreate,
    SavedConfigurationRead,
    SavedConfigurationRunRead,
    SavedConfigurationRunRequest,
    SavedConfigurationUpdate,
    WorkspaceRead,
    WorkspaceReportItem,
    WorkspaceResearchItem,
    WorkspaceUpdate,
)


class WorkspaceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = WorkspaceRepository(db)
        self.projects = ProjectRepository(db)

    def get(self, user_id: int) -> WorkspaceRead:
        workspace = self.repository.get_or_create(user_id)
        recent = self.repository.recent_research()
        scores = self.repository.latest_scores([item.id for item in recent])
        projects = self.projects.list(workspace.id)
        return WorkspaceRead(
            id=workspace.id,
            user_id=workspace.user_id,
            name=workspace.name,
            settings=workspace.settings,
            recent_research=[WorkspaceResearchItem.model_validate(item) for item in recent],
            recent_reports=[
                WorkspaceReportItem(
                    research_id=item.id,
                    title=item.title,
                    visibility_score=scores[item.id].visibility_score
                    if item.id in scores
                    else None,
                    calculated_at=scores[item.id].calculated_at if item.id in scores else None,
                )
                for item in recent
            ],
            favorite_projects=[
                {"id": item.id, "name": item.name, "tags": item.tags}
                for item in projects
                if item.favorite
            ],
            total_research=self.repository.total_research(),
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )

    def update(self, user_id: int, payload: WorkspaceUpdate) -> WorkspaceRead:
        workspace = self.repository.get_or_create(user_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(workspace, field, value)
        self.db.commit()
        self.db.refresh(workspace)
        return self.get(user_id)


class ProjectService:
    def __init__(self, db: Session, launcher: ResearchLaunchPort | None = None) -> None:
        self.db = db
        self.workspaces = WorkspaceRepository(db)
        self.projects = ProjectRepository(db)
        self.competitors = CompetitorRepository(db)
        self.domains = DomainRepository(db)
        self.configurations = SavedConfigurationRepository(db)
        self.bulk_runs = BulkResearchRepository(db)
        self.launcher = launcher

    def _workspace_id(self, user_id: int) -> int:
        return self.workspaces.get_or_create(user_id).id

    def _read_many(self, projects: list[Project]) -> list[ProjectRead]:
        counts = self.projects.research_counts([item.id for item in projects])
        return [
            ProjectRead.model_validate(item).model_copy(
                update={"research_count": counts.get(item.id, 0)}
            )
            for item in projects
        ]

    def list(self, user_id: int, include_archived: bool = False) -> list[ProjectRead]:
        return self._read_many(
            self.projects.list(self._workspace_id(user_id), include_archived=include_archived)
        )

    def get(self, user_id: int, project_id: int) -> ProjectRead:
        return self._read_many([self.projects.get(self._workspace_id(user_id), project_id)])[0]

    def create(self, user_id: int, payload: ProjectCreate) -> ProjectRead:
        project = self.projects.save(
            Project(workspace_id=self._workspace_id(user_id), **payload.model_dump())
        )
        return self._read_many([project])[0]

    def update(self, user_id: int, project_id: int, payload: ProjectUpdate) -> ProjectRead:
        project = self.projects.get(self._workspace_id(user_id), project_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        return self._read_many([self.projects.save(project)])[0]

    def delete(self, user_id: int, project_id: int) -> None:
        project = self.projects.get(self._workspace_id(user_id), project_id)
        self.db.delete(project)
        self.db.commit()

    def list_competitors(self, user_id: int, project_id: int) -> list[CompetitorRead]:
        self.projects.get(self._workspace_id(user_id), project_id)
        return [CompetitorRead.model_validate(item) for item in self.competitors.list(project_id)]

    def create_competitor(
        self, user_id: int, project_id: int, payload: CompetitorCreate
    ) -> CompetitorRead:
        self.projects.get(self._workspace_id(user_id), project_id)
        return CompetitorRead.model_validate(
            self.competitors.save(ProjectCompetitor(project_id=project_id, **payload.model_dump()))
        )

    def update_competitor(
        self,
        user_id: int,
        project_id: int,
        competitor_id: int,
        payload: CompetitorUpdate,
    ) -> CompetitorRead:
        self.projects.get(self._workspace_id(user_id), project_id)
        item = self.competitors.get(project_id, competitor_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        return CompetitorRead.model_validate(self.competitors.save(item))

    def delete_competitor(self, user_id: int, project_id: int, competitor_id: int) -> None:
        self.projects.get(self._workspace_id(user_id), project_id)
        item = self.competitors.get(project_id, competitor_id)
        self.db.delete(item)
        self.db.commit()

    def import_competitors(
        self, user_id: int, project_id: int, payload: CompetitorImport
    ) -> list[CompetitorRead]:
        self.projects.get(self._workspace_id(user_id), project_id)
        existing = {item.name.casefold(): item for item in self.competitors.list(project_id)}
        for incoming in payload.competitors:
            item = existing.get(incoming.name.casefold())
            if item is None:
                item = ProjectCompetitor(project_id=project_id, **incoming.model_dump())
            else:
                for field, value in incoming.model_dump().items():
                    setattr(item, field, value)
            self.db.add(item)
        self.db.commit()
        return self.list_competitors(user_id, project_id)

    @staticmethod
    def _hostname(value: str) -> tuple[str, str]:
        candidate = value.strip()
        parsed = urlsplit(candidate if "://" in candidate else f"//{candidate}")
        host = (parsed.hostname or "").rstrip(".").casefold()
        if not host or len(host) > 253 or "." not in host:
            raise ValueError("A valid domain hostname is required")
        try:
            ascii_host = host.encode("idna").decode("ascii")
        except UnicodeError as error:
            raise ValueError("A valid domain hostname is required") from error
        return ascii_host, host

    def list_domains(self, user_id: int, project_id: int) -> list[DomainRead]:
        self.projects.get(self._workspace_id(user_id), project_id)
        return [DomainRead.model_validate(item) for item in self.domains.list(project_id)]

    def create_domain(
        self, user_id: int, project_id: int, payload: DomainCreate
    ) -> DomainRead:
        self.projects.get(self._workspace_id(user_id), project_id)
        hostname, display = self._hostname(payload.hostname)
        values = payload.model_dump(exclude={"hostname", "display_name"})
        item = ProjectDomain(
            project_id=project_id,
            hostname=hostname,
            display_name=payload.display_name or display,
            **values,
        )
        if not self.domains.list(project_id):
            item.is_primary = True
        return DomainRead.model_validate(self.domains.save(item))

    def update_domain(
        self,
        user_id: int,
        project_id: int,
        domain_id: int,
        payload: DomainUpdate,
    ) -> DomainRead:
        self.projects.get(self._workspace_id(user_id), project_id)
        item = self.domains.get(project_id, domain_id)
        changes = payload.model_dump(exclude_unset=True)
        if "hostname" in changes:
            item.hostname, default_display = self._hostname(changes.pop("hostname"))
            if "display_name" not in changes:
                item.display_name = default_display
        for field, value in changes.items():
            setattr(item, field, value)
        return DomainRead.model_validate(self.domains.save(item))

    def delete_domain(self, user_id: int, project_id: int, domain_id: int) -> None:
        self.projects.get(self._workspace_id(user_id), project_id)
        item = self.domains.get(project_id, domain_id)
        self.db.delete(item)
        self.db.commit()

    def import_domains(
        self, user_id: int, project_id: int, payload: DomainImport
    ) -> list[DomainRead]:
        self.projects.get(self._workspace_id(user_id), project_id)
        existing = {item.hostname: item for item in self.domains.list(project_id)}
        for incoming in payload.domains:
            hostname, display = self._hostname(incoming.hostname)
            item = existing.get(hostname)
            values = incoming.model_dump(exclude={"hostname", "display_name"})
            if item is None:
                item = ProjectDomain(
                    project_id=project_id,
                    hostname=hostname,
                    display_name=incoming.display_name or display,
                    **values,
                )
            else:
                item.display_name = incoming.display_name or display
                for field, value in values.items():
                    setattr(item, field, value)
            self.domains.save(item)
        return self.list_domains(user_id, project_id)

    def list_configurations(
        self, user_id: int, project_id: int
    ) -> list[SavedConfigurationRead]:
        self.projects.get(self._workspace_id(user_id), project_id)
        return [
            SavedConfigurationRead.model_validate(item)
            for item in self.configurations.list(project_id)
        ]

    def create_configuration(
        self, user_id: int, project_id: int, payload: SavedConfigurationCreate
    ) -> SavedConfigurationRead:
        self.projects.get(self._workspace_id(user_id), project_id)
        item = SavedResearchConfiguration(
            project_id=project_id, **payload.model_dump(mode="json")
        )
        return SavedConfigurationRead.model_validate(self.configurations.save(item))

    def update_configuration(
        self,
        user_id: int,
        project_id: int,
        configuration_id: int,
        payload: SavedConfigurationUpdate,
    ) -> SavedConfigurationRead:
        self.projects.get(self._workspace_id(user_id), project_id)
        item = self.configurations.get(project_id, configuration_id)
        for field, value in payload.model_dump(exclude_unset=True, mode="json").items():
            setattr(item, field, value)
        return SavedConfigurationRead.model_validate(self.configurations.save(item))

    def delete_configuration(
        self, user_id: int, project_id: int, configuration_id: int
    ) -> None:
        self.projects.get(self._workspace_id(user_id), project_id)
        item = self.configurations.get(project_id, configuration_id)
        self.db.delete(item)
        self.db.commit()

    def run_configuration(
        self,
        user_id: int,
        project_id: int,
        configuration_id: int,
        payload: SavedConfigurationRunRequest,
    ) -> SavedConfigurationRunRead:
        project = self.projects.get(self._workspace_id(user_id), project_id)
        configuration = self.configurations.get(project_id, configuration_id)
        if payload.domain_id is not None:
            self.domains.get(project_id, payload.domain_id)
        if self.launcher is None:
            raise RuntimeError("Research launcher is not configured")
        receipt = self.launcher.launch(
            ResearchLaunchRequest(
                project_id=project_id,
                domain_id=payload.domain_id,
                title=payload.title or f"{project.name}: {configuration.name}",
                query=payload.query or f"Run {configuration.template_code} for {project.name}",
                routing_profile=RoutingProfile(configuration.routing_profile),
                languages=configuration.languages,
                regions=configuration.regions,
                template_code=configuration.template_code,
            )
        )
        return SavedConfigurationRunRead(
            research_id=receipt.research_id,
            job_id=receipt.job_id,
            state=receipt.state,
        )

    @staticmethod
    def _bulk_state(research_state: str) -> str:
        if research_state == "COMPLETED":
            return "COMPLETED"
        if research_state in {"FAILED", "ARCHIVED"}:
            return "FAILED"
        return "PENDING"

    def _read_bulk_run(self, run: BulkResearchRun) -> BulkResearchRead:
        items = self.bulk_runs.items(run.id)
        if self.launcher is not None:
            states = self.launcher.statuses([item.research_id for item in items])
            normalized = {
                research_id: self._bulk_state(state)
                for research_id, state in states.items()
            }
            self.bulk_runs.update_states(items, normalized)
        completed = sum(item.state == "COMPLETED" for item in items)
        failed = sum(item.state == "FAILED" for item in items)
        finished = completed + failed
        return BulkResearchRead(
            id=run.id,
            project_id=run.project_id,
            name=run.name,
            template_code=run.template_code,
            routing_profile=RoutingProfile(run.routing_profile),
            total_items=run.total_items,
            pending_items=run.total_items - finished,
            completed_items=completed,
            failed_items=failed,
            progress_percent=round(finished / run.total_items * 100, 2),
            items=[BulkResearchItemRead.model_validate(item) for item in items],
            created_at=run.created_at,
        )

    def create_bulk_run(
        self, user_id: int, project_id: int, payload: BulkResearchCreate
    ) -> BulkResearchRead:
        self.projects.get(self._workspace_id(user_id), project_id)
        if self.launcher is None:
            raise RuntimeError("Research launcher is not configured")
        brands = [target.brand.strip() for target in payload.targets]
        if len(set(brands)) != len(brands):
            raise ValueError("Bulk research brands must be unique")
        for target in payload.targets:
            if target.domain_id is not None:
                self.domains.get(project_id, target.domain_id)
        run = self.bulk_runs.save_run(
            BulkResearchRun(
                project_id=project_id,
                name=payload.name,
                template_code=payload.template_code,
                routing_profile=payload.routing_profile.value,
                total_items=len(payload.targets),
            )
        )
        for target in payload.targets:
            query = target.query or f"Analyze AI visibility for {target.brand}"
            receipt = self.launcher.launch(
                ResearchLaunchRequest(
                    project_id=project_id,
                    domain_id=target.domain_id,
                    title=f"{payload.name}: {target.brand}",
                    query=query,
                    routing_profile=payload.routing_profile,
                    languages=payload.languages,
                    regions=payload.regions,
                    template_code=payload.template_code,
                )
            )
            self.bulk_runs.add_item(
                BulkResearchItem(
                    bulk_run_id=run.id,
                    brand=target.brand.strip(),
                    domain_id=target.domain_id,
                    research_id=receipt.research_id,
                    job_id=receipt.job_id,
                    state=receipt.state,
                )
            )
        return self._read_bulk_run(run)

    def list_bulk_runs(self, user_id: int, project_id: int) -> list[BulkResearchRead]:
        self.projects.get(self._workspace_id(user_id), project_id)
        return [self._read_bulk_run(run) for run in self.bulk_runs.list_runs(project_id)]

    def get_bulk_run(
        self, user_id: int, project_id: int, run_id: int
    ) -> BulkResearchRead:
        self.projects.get(self._workspace_id(user_id), project_id)
        return self._read_bulk_run(self.bulk_runs.get_run(project_id, run_id))


__all__ = ["ProjectNotFoundError", "ProjectService", "WorkspaceService"]
