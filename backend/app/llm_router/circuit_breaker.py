from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.llm_router.config_loader import router_config
from backend.app.llm_router.metrics import CIRCUIT_STATE
from backend.app.llm_router.models import CircuitBreakerRecord
from backend.app.llm_router.schemas import CircuitState

STATE_VALUE = {
    CircuitState.CLOSED: 0,
    CircuitState.HALF_OPEN: 1,
    CircuitState.OPEN: 2,
}


def _settings() -> dict:
    return router_config().get("defaults", {})


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def allow_request(db: Session, model_id: str) -> bool:
    record = db.get(CircuitBreakerRecord, model_id)
    if record is None or record.state == CircuitState.CLOSED:
        return True
    if record.state == CircuitState.HALF_OPEN:
        return True
    recovery = timedelta(seconds=_settings().get("circuit_recovery_seconds", 60))
    if record.opened_at and datetime.now(UTC) - _as_utc(record.opened_at) >= recovery:
        record.state = CircuitState.HALF_OPEN
        record.success_count = 0
        record.updated_at = datetime.now(UTC)
        db.commit()
        CIRCUIT_STATE.labels(model=model_id).set(STATE_VALUE[CircuitState.HALF_OPEN])
        return True
    return False


def record_failure(db: Session, model_id: str) -> CircuitBreakerRecord:
    record = db.get(CircuitBreakerRecord, model_id)
    if record is None:
        record = CircuitBreakerRecord(
            model_id=model_id,
            state=CircuitState.CLOSED,
            failure_count=0,
            success_count=0,
            updated_at=datetime.now(UTC),
        )
        db.add(record)
    record.failure_count += 1
    record.success_count = 0
    record.last_failure_at = datetime.now(UTC)
    threshold = _settings().get("circuit_failure_threshold", 3)
    if record.failure_count >= threshold:
        record.state = CircuitState.OPEN
        record.opened_at = datetime.now(UTC)
    record.updated_at = datetime.now(UTC)
    db.commit()
    CIRCUIT_STATE.labels(model=model_id).set(STATE_VALUE[CircuitState(record.state)])
    return record


def record_success(db: Session, model_id: str) -> CircuitBreakerRecord:
    record = db.get(CircuitBreakerRecord, model_id)
    if record is None:
        record = CircuitBreakerRecord(
            model_id=model_id,
            state=CircuitState.CLOSED,
            failure_count=0,
            success_count=0,
            updated_at=datetime.now(UTC),
        )
        db.add(record)
    if record.state == CircuitState.HALF_OPEN:
        record.success_count += 1
        if record.success_count >= _settings().get("half_open_success_threshold", 2):
            record.state = CircuitState.CLOSED
            record.failure_count = 0
            record.opened_at = None
    else:
        record.failure_count = 0
    record.updated_at = datetime.now(UTC)
    db.commit()
    CIRCUIT_STATE.labels(model=model_id).set(STATE_VALUE[CircuitState(record.state)])
    return record
