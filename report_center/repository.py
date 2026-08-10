from sqlalchemy import select
from sqlalchemy.orm import Session

from report_center.models import ReportCatalogEntry


class ReportCatalogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def metadata(self, research_ids: list[int]) -> dict[int, ReportCatalogEntry]:
        if not research_ids:
            return {}
        rows = self.db.scalars(
            select(ReportCatalogEntry).where(
                ReportCatalogEntry.research_id.in_(research_ids)
            )
        )
        return {row.research_id: row for row in rows}

    def get_or_create(self, research_id: int, project_id: int) -> ReportCatalogEntry:
        item = self.db.scalar(
            select(ReportCatalogEntry).where(
                ReportCatalogEntry.research_id == research_id
            )
        )
        if item is None:
            item = ReportCatalogEntry(research_id=research_id, project_id=project_id)
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
        return item

    def save(self, item: ReportCatalogEntry) -> ReportCatalogEntry:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
