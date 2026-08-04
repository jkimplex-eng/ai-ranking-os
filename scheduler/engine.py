import calendar
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scheduler.models import (
    Schedule,
    ScheduleExecution,
    ScheduleExecutionStatus,
    ScheduleHistory,
    ScheduleType,
)
from scheduler.ports import (
    ResearchLauncher,
    ResearchLaunchRequest,
    ScheduledModel,
)
from scheduler.schemas import (
    RetryPolicy,
    ScheduleCreate,
    ScheduleExecutionRead,
    ScheduleHistoryRead,
    ScheduleRead,
    ScheduleUpdate,
)


class ScheduleNotFoundError(LookupError):
    """Requested schedule does not exist."""


class InvalidCronExpressionError(ValueError):
    """Cron expression is invalid or cannot produce a future run."""


def next_run_at(
    schedule_type: ScheduleType,
    after: datetime,
    cron_expression: str | None = None,
) -> datetime:
    after = _aware(after)
    if schedule_type == ScheduleType.HOURLY:
        return after + timedelta(hours=1)
    if schedule_type == ScheduleType.DAILY:
        return after + timedelta(days=1)
    if schedule_type == ScheduleType.WEEKLY:
        return after + timedelta(weeks=1)
    if schedule_type == ScheduleType.MONTHLY:
        year, month = after.year, after.month + 1
        if month == 13:
            year, month = year + 1, 1
        day = min(after.day, calendar.monthrange(year, month)[1])
        return after.replace(year=year, month=month, day=day)
    if cron_expression is None:
        raise InvalidCronExpressionError("CRON schedule requires cron_expression")
    return _next_cron(cron_expression, after)


class SchedulerEngine:
    def __init__(
        self,
        db: Session,
        launcher: ResearchLauncher,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.db = db
        self.launcher = launcher
        self.clock = clock
        self.sleeper = sleeper

    def create(self, payload: ScheduleCreate) -> ScheduleRead:
        now = _aware(self.clock())
        base = _aware(payload.start_at) if payload.start_at else now
        run_at = base if payload.start_at and base >= now else next_run_at(
            payload.schedule_type, base, payload.cron_expression
        )
        if payload.schedule_type == ScheduleType.CRON:
            cron_after = base - timedelta(minutes=1) if payload.start_at else now
            run_at = _next_cron(str(payload.cron_expression), cron_after)
            if run_at < now:
                run_at = _next_cron(str(payload.cron_expression), now)
        schedule = Schedule(
            name=payload.name,
            research_id=payload.research_id,
            schedule_type=payload.schedule_type,
            cron_expression=payload.cron_expression,
            models=[model.model_dump() for model in payload.models],
            query=payload.query,
            retry_policy=payload.retry_policy.model_dump(),
            is_enabled=payload.is_enabled,
            next_run_at=run_at,
        )
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return self._schedule_read(schedule)

    def list(self) -> list[ScheduleRead]:
        schedules = self.db.scalars(select(Schedule).order_by(Schedule.id)).all()
        return [self._schedule_read(schedule) for schedule in schedules]

    def update(self, schedule_id: int, payload: ScheduleUpdate) -> ScheduleRead:
        schedule = self._get(schedule_id)
        changes = payload.model_dump(exclude_unset=True)
        if "models" in changes:
            changes["models"] = [model.model_dump() for model in payload.models or []]
        if "retry_policy" in changes and payload.retry_policy is not None:
            changes["retry_policy"] = payload.retry_policy.model_dump()
        for field, value in changes.items():
            setattr(schedule, field, value)
        if "schedule_type" in changes or "cron_expression" in changes:
            if schedule.schedule_type == ScheduleType.CRON and not schedule.cron_expression:
                raise InvalidCronExpressionError("CRON schedule requires cron_expression")
            if schedule.schedule_type != ScheduleType.CRON:
                schedule.cron_expression = None
            schedule.next_run_at = next_run_at(
                schedule.schedule_type, _aware(self.clock()), schedule.cron_expression
            )
        self.db.commit()
        self.db.refresh(schedule)
        return self._schedule_read(schedule)

    def delete(self, schedule_id: int) -> None:
        schedule = self._get(schedule_id)
        self.db.delete(schedule)
        self.db.commit()

    def run_due(self) -> list[ScheduleExecutionRead]:
        now = _aware(self.clock())
        schedules = self.db.scalars(
            select(Schedule)
            .where(Schedule.is_enabled.is_(True), Schedule.next_run_at <= now)
            .order_by(Schedule.next_run_at, Schedule.id)
            .with_for_update(skip_locked=True)
        ).all()
        results = []
        for schedule in schedules:
            execution = self._claim(schedule, now)
            if execution is None:
                continue
            results.append(self._execute(schedule, execution))
        return results

    def _claim(self, schedule: Schedule, now: datetime) -> ScheduleExecution | None:
        active = self.db.scalar(
            select(ScheduleExecution.id).where(
                ScheduleExecution.schedule_id == schedule.id,
                ScheduleExecution.status == ScheduleExecutionStatus.RUNNING,
            )
        )
        if active is not None:
            return None
        scheduled_for = _aware(schedule.next_run_at)
        execution = ScheduleExecution(
            schedule_id=schedule.id,
            status=ScheduleExecutionStatus.RUNNING,
            attempts=0,
            scheduled_for=scheduled_for,
            started_at=now,
        )
        schedule.last_run_at = now
        schedule.next_run_at = next_run_at(
            schedule.schedule_type, scheduled_for, schedule.cron_expression
        )
        self.db.add(execution)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return None
        self.db.refresh(execution)
        return execution

    def _execute(
        self, schedule: Schedule, execution: ScheduleExecution
    ) -> ScheduleExecutionRead:
        policy = RetryPolicy.model_validate(schedule.retry_policy)
        for attempt in range(1, policy.max_attempts + 1):
            started = _aware(self.clock())
            delay = policy.base_delay_seconds * (2 ** (attempt - 2)) if attempt > 1 else 0
            if delay:
                self.sleeper(delay)
            research_id = None
            error = None
            try:
                result = self.launcher.launch(
                    ResearchLaunchRequest(
                        template_research_id=schedule.research_id,
                        models=tuple(ScheduledModel(**item) for item in schedule.models),
                        query=schedule.query,
                    )
                )
                research_id = result.research_id
                if not result.succeeded:
                    error = result.error or "Scheduled research failed"
            except Exception as exception:  # noqa: BLE001 - persisted retry boundary
                error = str(exception)
            finished = _aware(self.clock())
            execution.attempts = attempt
            execution.research_id = research_id
            execution.error = error
            execution.history.append(
                ScheduleHistory(
                    attempt=attempt,
                    status=(
                        ScheduleExecutionStatus.COMPLETED
                        if error is None
                        else ScheduleExecutionStatus.FAILED
                    ),
                    research_id=research_id,
                    error=error,
                    retry_delay_seconds=delay,
                    started_at=started,
                    finished_at=finished,
                )
            )
            if error is None:
                execution.status = ScheduleExecutionStatus.COMPLETED
                break
        else:
            execution.status = ScheduleExecutionStatus.FAILED
        execution.finished_at = _aware(self.clock())
        self.db.commit()
        return self._execution_read(execution)

    def _get(self, schedule_id: int) -> Schedule:
        schedule = self.db.get(Schedule, schedule_id)
        if schedule is None:
            raise ScheduleNotFoundError(f"Schedule {schedule_id} not found")
        return schedule

    @staticmethod
    def _schedule_read(schedule: Schedule) -> ScheduleRead:
        return ScheduleRead(
            id=schedule.id,
            name=schedule.name,
            research_id=schedule.research_id,
            schedule_type=schedule.schedule_type,
            cron_expression=schedule.cron_expression,
            models=schedule.models,
            query=schedule.query,
            retry_policy=schedule.retry_policy,
            is_enabled=schedule.is_enabled,
            next_run_at=_aware(schedule.next_run_at),
            last_run_at=_aware(schedule.last_run_at) if schedule.last_run_at else None,
            created_at=_aware(schedule.created_at),
            updated_at=_aware(schedule.updated_at),
        )

    @staticmethod
    def _execution_read(execution: ScheduleExecution) -> ScheduleExecutionRead:
        return ScheduleExecutionRead(
            id=execution.id,
            schedule_id=execution.schedule_id,
            research_id=execution.research_id,
            status=execution.status,
            attempts=execution.attempts,
            error=execution.error,
            scheduled_for=_aware(execution.scheduled_for),
            started_at=_aware(execution.started_at),
            finished_at=_aware(execution.finished_at) if execution.finished_at else None,
            history=[
                ScheduleHistoryRead(
                    id=item.id,
                    attempt=item.attempt,
                    status=item.status,
                    research_id=item.research_id,
                    error=item.error,
                    retry_delay_seconds=item.retry_delay_seconds,
                    started_at=_aware(item.started_at),
                    finished_at=_aware(item.finished_at),
                )
                for item in execution.history
            ],
        )


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _next_cron(expression: str, after: datetime) -> datetime:
    parts = expression.split()
    if len(parts) != 5:
        raise InvalidCronExpressionError("Cron expression must contain five fields")
    limits = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 6))
    allowed = [_cron_values(part, *limit) for part, limit in zip(parts, limits, strict=True)]
    candidate = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    deadline = candidate + timedelta(days=366 * 5)
    while candidate <= deadline:
        cron_weekday = (candidate.weekday() + 1) % 7
        time_matches = (
            candidate.minute in allowed[0]
            and candidate.hour in allowed[1]
            and candidate.month in allowed[3]
        )
        day_of_month_matches = candidate.day in allowed[2]
        day_of_week_matches = cron_weekday in allowed[4]
        if parts[2] != "*" and parts[4] != "*":
            day_matches = day_of_month_matches or day_of_week_matches
        else:
            day_matches = day_of_month_matches and day_of_week_matches
        if time_matches and day_matches:
            return candidate
        candidate += timedelta(minutes=1)
    raise InvalidCronExpressionError("Cron expression has no run within five years")


def _cron_values(field: str, minimum: int, maximum: int) -> set[int]:
    values: set[int] = set()
    for token in field.split(","):
        step = 1
        if "/" in token:
            token, raw_step = token.split("/", 1)
            try:
                step = int(raw_step)
            except ValueError as error:
                raise InvalidCronExpressionError("Invalid cron step") from error
            if step < 1:
                raise InvalidCronExpressionError("Cron step must be positive")
        if token == "*":
            start, end = minimum, maximum
        elif "-" in token:
            try:
                start, end = (int(value) for value in token.split("-", 1))
            except ValueError as error:
                raise InvalidCronExpressionError("Invalid cron range") from error
        else:
            try:
                start = end = int(token)
            except ValueError as error:
                raise InvalidCronExpressionError("Invalid cron value") from error
        if start < minimum or end > maximum or start > end:
            raise InvalidCronExpressionError("Cron value outside allowed range")
        values.update(range(start, end + 1, step))
    return values
