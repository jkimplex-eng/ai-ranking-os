from sqlalchemy import select
from sqlalchemy.orm import Session

from project_monitoring.models import ProjectMonitor


class MonitorRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, project_id: int) -> ProjectMonitor | None:
        return self.db.scalar(
            select(ProjectMonitor).where(ProjectMonitor.project_id == project_id)
        )

    def save(self, monitor: ProjectMonitor) -> ProjectMonitor:
        self.db.add(monitor)
        self.db.commit()
        self.db.refresh(monitor)
        return monitor

    def delete(self, monitor: ProjectMonitor) -> None:
        self.db.delete(monitor)
        self.db.commit()
