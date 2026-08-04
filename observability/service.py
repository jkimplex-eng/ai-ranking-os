from sqlalchemy import text
from sqlalchemy.orm import Session

from observability.ports import HealthCheck


class DatabaseHealthCheck:
    name = "database"

    def __init__(self, db: Session):
        self.db = db

    def check(self):
        try:
            self.db.execute(text("SELECT 1"))
            return True, "available"
        except Exception:
            return False, "unavailable"


class ObservabilityService:
    def __init__(self, checks: list[HealthCheck]):
        self.checks = checks

    def status(self):
        values = {
            check.name: {"healthy": ok, "detail": detail}
            for check in self.checks
            for ok, detail in [check.check()]
        }
        return {
            "status": "healthy" if all(x["healthy"] for x in values.values()) else "degraded",
            "checks": values,
        }
