from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status

from closed_beta.dependencies import BetaAdminId, BetaServiceDependency
from closed_beta.models import BetaAccessStatus
from closed_beta.schemas import (
    BetaUserRead,
    BetaUserUpdate,
    InvitationAccept,
    InvitationAccepted,
    InvitationCreate,
    InvitationCreated,
    InvitationRead,
)
from closed_beta.service import BetaAdminError, BetaNotFoundError

router = APIRouter(tags=["closed-beta"])


def _correlation(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid4())


@router.get("/admin/beta/users", response_model=list[BetaUserRead])
def list_beta_users(
    service: BetaServiceDependency,
    _admin_id: BetaAdminId,
    search: str | None = Query(default=None, max_length=200),
    beta_status: Annotated[
        BetaAccessStatus | None, Query(alias="status")
    ] = None,
    active: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[BetaUserRead]:
    return service.users(search, beta_status, active)[offset : offset + limit]


@router.patch("/admin/beta/users/{user_id}", response_model=BetaUserRead)
def update_beta_user(
    user_id: int,
    payload: BetaUserUpdate,
    request: Request,
    service: BetaServiceDependency,
    admin_id: BetaAdminId,
) -> BetaUserRead:
    try:
        return service.update_user(user_id, payload, str(admin_id), _correlation(request))
    except BetaNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/admin/beta/invitations",
    response_model=InvitationCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_invitation(
    payload: InvitationCreate,
    request: Request,
    service: BetaServiceDependency,
    admin_id: BetaAdminId,
) -> InvitationCreated:
    try:
        return service.create_invitation(payload, str(admin_id), _correlation(request))
    except BetaAdminError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/admin/beta/invitations", response_model=list[InvitationRead])
def list_invitations(
    service: BetaServiceDependency, _admin_id: BetaAdminId
) -> list[InvitationRead]:
    return service.invitations()


@router.post(
    "/admin/beta/invitations/{invitation_id}/revoke",
    response_model=InvitationRead,
)
def revoke_invitation(
    invitation_id: int,
    request: Request,
    service: BetaServiceDependency,
    admin_id: BetaAdminId,
) -> InvitationRead:
    try:
        return service.revoke_invitation(
            invitation_id, str(admin_id), _correlation(request)
        )
    except BetaNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/admin/beta/invitations/{invitation_id}/resend",
    response_model=InvitationCreated,
)
def resend_invitation(
    invitation_id: int,
    request: Request,
    service: BetaServiceDependency,
    admin_id: BetaAdminId,
) -> InvitationCreated:
    try:
        return service.resend_invitation(
            invitation_id, str(admin_id), _correlation(request)
        )
    except BetaNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/beta/invitations/{token}/accept", response_model=InvitationAccepted
)
def accept_invitation(
    token: str, payload: InvitationAccept, service: BetaServiceDependency
) -> InvitationAccepted:
    try:
        return service.accept(token, payload)
    except (BetaNotFoundError, ValueError) as error:
        raise HTTPException(status_code=404, detail="Invitation is unavailable") from error
