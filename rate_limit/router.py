from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from backend.app.database import get_db
from rate_limit.backend import MemoryRateLimitBackend
from rate_limit.repository import RateLimitRepository
from rate_limit.schemas import PolicyCreate, PolicyRead, RateCheck, RateDecisionRead
from rate_limit.service import RateLimitError, RateLimitService

router = APIRouter(prefix="/rate-limits", tags=["rate-limits"])
_backend = MemoryRateLimitBackend()


def get_rate_limit_service(db: Annotated[Session, Depends(get_db)]):
    return RateLimitService(RateLimitRepository(db), _backend)


Service = Annotated[RateLimitService, Depends(get_rate_limit_service)]


@router.post("/policies", response_model=PolicyRead, status_code=201)
def create(payload: PolicyCreate, service: Service):
    return service.create(payload)


@router.get("/policies", response_model=list[PolicyRead])
def policies(service: Service):
    return service.list()


@router.post("/check", response_model=RateDecisionRead)
def check(payload: RateCheck, response: Response, service: Service):
    try:
        decision = service.check(payload.policy_id, payload.subject)
    except RateLimitError as error:
        raise HTTPException(404, str(error)) from error
    if not decision.allowed:
        response.status_code = 429
        response.headers["Retry-After"] = str(max(1, int(decision.retry_after_seconds + 0.999)))
    return RateDecisionRead(**decision.__dict__)
