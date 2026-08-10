from sqlalchemy import func, select
from sqlalchemy.orm import Session

from closed_beta.ports import UsagePort
from research.models import Research
from workspace.models import Project, UserWorkspace


class WorkspaceBetaUsage(UsagePort):
    def __init__(self, db: Session) -> None:
        self.db = db

    def research_counts(self, user_ids: list[int]) -> dict[int, int]:
        if not user_ids:
            return {}
        rows = self.db.execute(
            select(UserWorkspace.user_id, func.count(Research.id))
            .outerjoin(Project, Project.workspace_id == UserWorkspace.id)
            .outerjoin(Research, Research.project_id == Project.id)
            .where(UserWorkspace.user_id.in_(user_ids))
            .group_by(UserWorkspace.user_id)
        )
        return {int(user_id): int(count) for user_id, count in rows}
