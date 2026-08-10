from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request, status

from report_sharing.dependencies import ShareServiceDependency
from report_sharing.schemas import ShareCreate, ShareCreated, SharedReportRead, ShareRead
from report_sharing.service import ShareAccessError

router = APIRouter(tags=["report-sharing"])


def _actor(request: Request) -> str:
    principal = getattr(request.state, "principal", None)
    return str(getattr(principal, "user_id", getattr(principal, "id", 1)))


def _correlation(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid4())


@router.post(
    "/reports/{research_id}/shares",
    response_model=ShareCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_share(
    research_id: int,
    payload: ShareCreate,
    request: Request,
    service: ShareServiceDependency,
) -> ShareCreated:
    try:
        return service.create(research_id, payload, _actor(request), _correlation(request))
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Report not found") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/reports/{research_id}/shares", response_model=list[ShareRead])
def list_shares(research_id: int, service: ShareServiceDependency) -> list[ShareRead]:
    return service.list(research_id)


@router.post("/reports/shares/{share_id}/revoke", response_model=ShareRead)
def revoke_share(
    share_id: int, request: Request, service: ShareServiceDependency
) -> ShareRead:
    try:
        return service.revoke(share_id, _actor(request), _correlation(request))
    except ShareAccessError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/reports/shares/{share_id}/rotate", response_model=ShareCreated)
def rotate_share(
    share_id: int, request: Request, service: ShareServiceDependency
) -> ShareCreated:
    try:
        return service.rotate(share_id, _actor(request), _correlation(request))
    except ShareAccessError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/shared/reports/{token}", response_model=SharedReportRead)
def open_shared_report(
    token: str,
    request: Request,
    service: ShareServiceDependency,
    password: str | None = Header(default=None, alias="X-Share-Password"),
) -> SharedReportRead:
    try:
        return service.open(
            token,
            password,
            request.client.host if request.client else None,
            request.headers.get("user-agent"),
            _correlation(request),
        )
    except ShareAccessError as error:
        raise HTTPException(status_code=404, detail="Share link is unavailable") from error
