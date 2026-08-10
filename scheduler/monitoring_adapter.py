from sqlalchemy.orm import Session

from project_monitoring.ports import MonitorScheduleRequest, MonitorScheduleResult
from research.models import Research
from scheduler.models import ScheduleType
from scheduler.research_adapter import build_scheduler_engine
from scheduler.schemas import ScheduleCreate, ScheduleModel, ScheduleUpdate


class SchedulerMonitorAdapter:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.engine = build_scheduler_engine(db)

    def validate_template(self, research_id: int, project_id: int) -> bool:
        research = self.db.get(Research, research_id)
        return research is not None and research.project_id == project_id

    @staticmethod
    def _result(schedule) -> MonitorScheduleResult:
        return MonitorScheduleResult(
            schedule_id=schedule.id, next_run_at=schedule.next_run_at
        )

    def create(self, request: MonitorScheduleRequest) -> MonitorScheduleResult:
        schedule = self.engine.create(
            ScheduleCreate(
                name=request.name,
                research_id=request.research_id,
                schedule_type=ScheduleType(request.frequency),
                models=[ScheduleModel(**item) for item in request.models],
                query=request.query,
                is_enabled=request.enabled,
            )
        )
        return self._result(schedule)

    def update(
        self, schedule_id: int, request: MonitorScheduleRequest
    ) -> MonitorScheduleResult:
        schedule = self.engine.update(
            schedule_id,
            ScheduleUpdate(
                name=request.name,
                schedule_type=ScheduleType(request.frequency),
                models=[ScheduleModel(**item) for item in request.models],
                query=request.query,
                is_enabled=request.enabled,
            ),
        )
        return self._result(schedule)

    def delete(self, schedule_id: int) -> None:
        self.engine.delete(schedule_id)
