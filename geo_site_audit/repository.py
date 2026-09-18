from sqlalchemy import select
from sqlalchemy.orm import Session

from geo_site_audit.models import GeoSiteAudit


class GeoSiteAuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, audit: GeoSiteAudit) -> GeoSiteAudit:
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        return audit

    def get(self, user_id: int, audit_id: int) -> GeoSiteAudit | None:
        return self.db.scalar(
            select(GeoSiteAudit).where(GeoSiteAudit.id == audit_id, GeoSiteAudit.user_id == user_id)
        )

    def list(self, user_id: int, project_id: int | None, limit: int) -> list[GeoSiteAudit]:
        query = select(GeoSiteAudit).where(GeoSiteAudit.user_id == user_id)
        if project_id is not None:
            query = query.where(GeoSiteAudit.project_id == project_id)
        return list(self.db.scalars(query.order_by(GeoSiteAudit.created_at.desc()).limit(limit)))
