from sqlalchemy import select
from sqlalchemy.orm import Session

from report_center.ports import ReportSourceItem
from research.models import Research, ResearchScore
from research.reporting import ReportingService


class SqlAlchemyReportSource:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_reports(self, project_id: int | None = None) -> list[ReportSourceItem]:
        statement = select(Research).order_by(Research.created_at.desc())
        if project_id is not None:
            statement = statement.where(Research.project_id == project_id)
        research = list(self.db.scalars(statement))
        result: list[ReportSourceItem] = []
        for item in research:
            if item.project_id is None:
                continue
            score = self.db.scalar(
                select(ResearchScore)
                .where(ResearchScore.research_id == item.id)
                .order_by(ResearchScore.calculated_at.desc())
            )
            result.append(
                ReportSourceItem(
                    research_id=item.id,
                    project_id=item.project_id,
                    title=item.title,
                    status=item.status.value,
                    visibility_score=score.visibility_score if score else None,
                    score_version=score.version if score else None,
                    created_at=item.created_at,
                )
            )
        return result

    def export_payload(self, research_id: int) -> dict:
        return ReportingService(self.db).get_report(research_id).model_dump(mode="json")
