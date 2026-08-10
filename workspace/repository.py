from sqlalchemy import func, select
from sqlalchemy.orm import Session

from research.models import Research, ResearchScore
from workspace.models import UserWorkspace


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
