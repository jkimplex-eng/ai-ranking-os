from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from alice_learning.models import AliceAutomationPlan, AliceAutomationRun, AliceQuerySet


class AliceAutomationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, item):
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def plan(self, plan_id: int) -> AliceAutomationPlan | None:
        return self.db.get(AliceAutomationPlan, plan_id)

    def plans(self, organization_id: int) -> list[AliceAutomationPlan]:
        return list(
            self.db.scalars(
                select(AliceAutomationPlan)
                .where(AliceAutomationPlan.organization_id == organization_id)
                .order_by(AliceAutomationPlan.id)
            )
        )

    def due(self, now: datetime) -> list[AliceAutomationPlan]:
        return list(
            self.db.scalars(
                select(AliceAutomationPlan)
                .where(
                    AliceAutomationPlan.is_enabled.is_(True), AliceAutomationPlan.next_run_at <= now
                )
                .order_by(AliceAutomationPlan.next_run_at, AliceAutomationPlan.id)
                .with_for_update(skip_locked=True)
            )
        )

    def active_run(self, plan_id: int) -> AliceAutomationRun | None:
        run = self.db.scalar(
            select(AliceAutomationRun).where(
                AliceAutomationRun.plan_id == plan_id, AliceAutomationRun.status == "RUNNING"
            )
        )
        if run is None:
            return None
        started = run.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        if datetime.now(UTC) - started <= timedelta(hours=2):
            return run
        # A worker restart can leave a RUNNING row behind. Release the
        # unique running slot so the next scheduled check can recover.
        run.status = "FAILED"
        run.finished_at = datetime.now(UTC)
        run.error = "Запуск прерван после тайм-аута восстановления worker"
        self.db.add(run)
        self.db.commit()
        return None

    def latest_query_set(self, plan_id: int, kind: str) -> AliceQuerySet | None:
        return self.db.scalar(
            select(AliceQuerySet)
            .where(AliceQuerySet.plan_id == plan_id, AliceQuerySet.kind == kind)
            .order_by(AliceQuerySet.version.desc())
        )

    def runs(self, organization_id: int, limit: int = 50) -> list[AliceAutomationRun]:
        return list(
            self.db.scalars(
                select(AliceAutomationRun)
                .join(AliceAutomationPlan, AliceAutomationPlan.id == AliceAutomationRun.plan_id)
                .where(AliceAutomationPlan.organization_id == organization_id)
                .order_by(AliceAutomationRun.started_at.desc(), AliceAutomationRun.id.desc())
                .limit(limit)
            )
        )
