from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_db
from hardening.repository import HardeningRepository
from hardening.schemas import DlqRead
from hardening.validation import validate_startup

router = APIRouter(prefix="/hardening", tags=["hardening"])


@router.get("/status")
def status():
    settings = get_settings()
    errors = validate_startup(settings)
    return {
        "status": "ready" if not errors else "invalid",
        "errors": errors,
        "controls": {
            "idempotency": True,
            "circuit_breaker": True,
            "retry": True,
            "timeout": True,
            "backpressure": True,
            "dead_letter_queue": True,
            "failover_port": True,
            "graceful_shutdown": True,
        },
    }


@router.get("/dlq", response_model=list[DlqRead])
def dlq(db: Annotated[Session, Depends(get_db)], status: str | None = None):
    return HardeningRepository(db).dlq(status)
