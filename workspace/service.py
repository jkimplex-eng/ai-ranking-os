from sqlalchemy.orm import Session

from workspace.models import Project, ProjectCompetitor
from workspace.repository import (
    CompetitorRepository,
    ProjectNotFoundError,
    ProjectRepository,
    WorkspaceRepository,
)
from workspace.schemas import (
    CompetitorCreate,
    CompetitorImport,
    CompetitorRead,
    CompetitorUpdate,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
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
    def __init__(self, db: Session) -> None:
        self.db = db
        self.workspaces = WorkspaceRepository(db)
        self.projects = ProjectRepository(db)
        self.competitors = CompetitorRepository(db)

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


__all__ = ["ProjectNotFoundError", "ProjectService", "WorkspaceService"]
