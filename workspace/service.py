from sqlalchemy.orm import Session

from workspace.repository import WorkspaceRepository
from workspace.schemas import (
    WorkspaceRead,
    WorkspaceReportItem,
    WorkspaceResearchItem,
    WorkspaceUpdate,
)


class WorkspaceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = WorkspaceRepository(db)

    def get(self, user_id: int) -> WorkspaceRead:
        workspace = self.repository.get_or_create(user_id)
        recent = self.repository.recent_research()
        scores = self.repository.latest_scores([item.id for item in recent])
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
