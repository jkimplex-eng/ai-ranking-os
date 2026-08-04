from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from observability.service import DatabaseHealthCheck, ObservabilityService

router = APIRouter(prefix="/observability", tags=["observability"])


def get_observability_service(db: Annotated[Session, Depends(get_db)]):
    return ObservabilityService([DatabaseHealthCheck(db)])


Service = Annotated[ObservabilityService, Depends(get_observability_service)]


@router.get("/liveness")
def liveness():
    return {"status": "alive"}


@router.get("/readiness")
def readiness(service: Service, response: Response) -> dict[str, Any]:
    result = service.status()
    if result["status"] != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@router.get("/health")
def health(service: Service):
    return service.status()
