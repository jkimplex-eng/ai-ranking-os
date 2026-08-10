from sqlalchemy import func, select
from sqlalchemy.orm import Session

from report_center.models import ReportCatalogEntry, ReportVersion


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

    def versions(self, research_id: int) -> list[ReportVersion]:
        return list(
            self.db.scalars(
                select(ReportVersion)
                .where(ReportVersion.research_id == research_id)
                .order_by(ReportVersion.version.desc())
            )
        )

    def version(self, research_id: int, version: int) -> ReportVersion | None:
        return self.db.scalar(
            select(ReportVersion).where(
                ReportVersion.research_id == research_id,
                ReportVersion.version == version,
            )
        )

    def add_version(
        self, entry: ReportCatalogEntry, checksum: str, payload: dict
    ) -> ReportVersion:
        existing = self.db.scalar(
            select(ReportVersion).where(
                ReportVersion.research_id == entry.research_id,
                ReportVersion.checksum == checksum,
            )
        )
        if existing is not None:
            return existing
        latest = int(
            self.db.scalar(
                select(func.max(ReportVersion.version)).where(
                    ReportVersion.research_id == entry.research_id
                )
            )
            or 0
        )
        version = ReportVersion(
            research_id=entry.research_id,
            catalog_entry_id=entry.id,
            version=latest + 1,
            checksum=checksum,
            payload=payload,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version
