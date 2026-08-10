from sqlalchemy import func, select
from sqlalchemy.orm import Session

from research.models import Research, ResearchScore
from workspace.models import (
    BulkResearchItem,
    BulkResearchRun,
    Project,
    ProjectCompetitor,
    ProjectDomain,
    SavedResearchConfiguration,
    UserWorkspace,
)


class WorkspaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self, user_id: int) -> UserWorkspace:
        workspace = self.db.scalar(
            select(UserWorkspace).where(UserWorkspace.user_id == user_id)
        )
        if workspace is None:
            workspace = UserWorkspace(user_id=user_id, name="Моё рабочее пространство", settings={})
            self.db.add(workspace)
            self.db.commit()
            self.db.refresh(workspace)
        return workspace

    def recent_research(self, limit: int = 8) -> list[Research]:
        return list(
            self.db.scalars(select(Research).order_by(Research.created_at.desc()).limit(limit))
        )

    def total_research(self) -> int:
        return int(self.db.scalar(select(func.count(Research.id))) or 0)

    def latest_scores(self, research_ids: list[int]) -> dict[int, ResearchScore]:
        if not research_ids:
            return {}
        rows = self.db.scalars(
            select(ResearchScore)
            .where(ResearchScore.research_id.in_(research_ids))
            .order_by(ResearchScore.research_id, ResearchScore.calculated_at.desc())
        )
        result: dict[int, ResearchScore] = {}
        for row in rows:
            result.setdefault(row.research_id, row)
        return result


class ProjectNotFoundError(LookupError):
    pass


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, workspace_id: int, *, include_archived: bool = False) -> list[Project]:
        statement = select(Project).where(Project.workspace_id == workspace_id)
        if not include_archived:
            statement = statement.where(Project.archived.is_(False))
        return list(
            self.db.scalars(
                statement.order_by(Project.favorite.desc(), Project.updated_at.desc())
            )
        )

    def get(self, workspace_id: int, project_id: int) -> Project:
        project = self.db.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
            )
        )
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        return project

    def save(self, project: Project) -> Project:
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def research_counts(self, project_ids: list[int]) -> dict[int, int]:
        if not project_ids:
            return {}
        rows = self.db.execute(
            select(Research.project_id, func.count(Research.id))
            .where(Research.project_id.in_(project_ids))
            .group_by(Research.project_id)
        )
        return {int(project_id): int(count) for project_id, count in rows}


class CompetitorRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, project_id: int) -> list[ProjectCompetitor]:
        return list(
            self.db.scalars(
                select(ProjectCompetitor)
                .where(ProjectCompetitor.project_id == project_id)
                .order_by(ProjectCompetitor.name)
            )
        )

    def get(self, project_id: int, competitor_id: int) -> ProjectCompetitor:
        item = self.db.scalar(
            select(ProjectCompetitor).where(
                ProjectCompetitor.id == competitor_id,
                ProjectCompetitor.project_id == project_id,
            )
        )
        if item is None:
            raise ProjectNotFoundError(f"Competitor {competitor_id} not found")
        return item

    def save(self, item: ProjectCompetitor) -> ProjectCompetitor:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item


class DomainRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, project_id: int) -> list[ProjectDomain]:
        return list(
            self.db.scalars(
                select(ProjectDomain)
                .where(ProjectDomain.project_id == project_id)
                .order_by(ProjectDomain.is_primary.desc(), ProjectDomain.hostname)
            )
        )

    def get(self, project_id: int, domain_id: int) -> ProjectDomain:
        item = self.db.scalar(
            select(ProjectDomain).where(
                ProjectDomain.id == domain_id,
                ProjectDomain.project_id == project_id,
            )
        )
        if item is None:
            raise ProjectNotFoundError(f"Domain {domain_id} not found")
        return item

    def save(self, item: ProjectDomain) -> ProjectDomain:
        if item.is_primary:
            for current in self.list(item.project_id):
                if current.id != item.id:
                    current.is_primary = False
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item


class SavedConfigurationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, project_id: int) -> list[SavedResearchConfiguration]:
        return list(
            self.db.scalars(
                select(SavedResearchConfiguration)
                .where(SavedResearchConfiguration.project_id == project_id)
                .order_by(SavedResearchConfiguration.name)
            )
        )

    def get(self, project_id: int, configuration_id: int) -> SavedResearchConfiguration:
        item = self.db.scalar(
            select(SavedResearchConfiguration).where(
                SavedResearchConfiguration.id == configuration_id,
                SavedResearchConfiguration.project_id == project_id,
            )
        )
        if item is None:
            raise ProjectNotFoundError(f"Saved configuration {configuration_id} not found")
        return item

    def save(self, item: SavedResearchConfiguration) -> SavedResearchConfiguration:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item


class BulkResearchRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save_run(self, run: BulkResearchRun) -> BulkResearchRun:
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def add_item(self, item: BulkResearchItem) -> BulkResearchItem:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_run(self, project_id: int, run_id: int) -> BulkResearchRun:
        run = self.db.scalar(
            select(BulkResearchRun).where(
                BulkResearchRun.id == run_id,
                BulkResearchRun.project_id == project_id,
            )
        )
        if run is None:
            raise ProjectNotFoundError(f"Bulk research run {run_id} not found")
        return run

    def list_runs(self, project_id: int) -> list[BulkResearchRun]:
        return list(
            self.db.scalars(
                select(BulkResearchRun)
                .where(BulkResearchRun.project_id == project_id)
                .order_by(BulkResearchRun.created_at.desc())
            )
        )

    def items(self, run_id: int) -> list[BulkResearchItem]:
        return list(
            self.db.scalars(
                select(BulkResearchItem)
                .where(BulkResearchItem.bulk_run_id == run_id)
                .order_by(BulkResearchItem.id)
            )
        )

    def update_states(self, items: list[BulkResearchItem], states: dict[int, str]) -> None:
        changed = False
        for item in items:
            state = states.get(item.research_id)
            if state is not None and state != item.state:
                item.state = state
                changed = True
        if changed:
            self.db.commit()
