from sqlalchemy import func, select
from sqlalchemy.orm import Session

from audit.models import AuditEvent


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def append(self, event: AuditEvent):
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def search(
        self,
        *,
        actor_id=None,
        action=None,
        category=None,
        correlation_id=None,
        page=1,
        page_size=50,
    ):
        query = select(AuditEvent)
        for column, value in (
            (AuditEvent.actor_id, actor_id),
            (AuditEvent.action, action),
            (AuditEvent.category, category),
            (AuditEvent.correlation_id, correlation_id),
        ):
            if value is not None:
                query = query.where(column == value)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self.db.scalars(
            query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(rows), total
