from fastapi import APIRouter, HTTPException, Query, Response, status

from organization_workspace.dependencies import CurrentUserId, OrganizationServiceDependency
from organization_workspace.schemas import (
    ActivityRead,
    InvitationAccept,
    InvitationCreate,
    InvitationRead,
    MemberRead,
    MemberRoleUpdate,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
    ProjectLink,
)
from organization_workspace.service import OrganizationError

router = APIRouter(prefix="/organizations", tags=["organization-workspace"])


def guard(call):
    try:
        return call()
    except OrganizationError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("", response_model=list[OrganizationRead])
def organizations(user_id: CurrentUserId, service: OrganizationServiceDependency):
    return service.list(user_id)


@router.post("", response_model=OrganizationRead, status_code=201)
def create(
    payload: OrganizationCreate, user_id: CurrentUserId, service: OrganizationServiceDependency
):
    return service.create(user_id, payload)


@router.patch("/{organization_id}", response_model=OrganizationRead)
def update(
    organization_id: int,
    payload: OrganizationUpdate,
    user_id: CurrentUserId,
    service: OrganizationServiceDependency,
):
    return guard(lambda: service.update(organization_id, user_id, payload))


@router.post("/{organization_id}/switch", response_model=OrganizationRead)
def switch(organization_id: int, user_id: CurrentUserId, service: OrganizationServiceDependency):
    return guard(lambda: service.switch(organization_id, user_id))


@router.get("/{organization_id}/members", response_model=list[MemberRead])
def members(organization_id: int, user_id: CurrentUserId, service: OrganizationServiceDependency):
    return guard(lambda: service.members(organization_id, user_id))


@router.patch("/{organization_id}/members/{member_id}", response_model=MemberRead)
def role(
    organization_id: int,
    member_id: int,
    payload: MemberRoleUpdate,
    user_id: CurrentUserId,
    service: OrganizationServiceDependency,
):
    return guard(lambda: service.update_role(organization_id, user_id, member_id, payload.role))


@router.delete("/{organization_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(
    organization_id: int,
    member_id: int,
    user_id: CurrentUserId,
    service: OrganizationServiceDependency,
):
    guard(lambda: service.remove_member(organization_id, user_id, member_id))
    return Response(status_code=204)


@router.post("/{organization_id}/invitations", response_model=InvitationRead, status_code=201)
def invite(
    organization_id: int,
    payload: InvitationCreate,
    user_id: CurrentUserId,
    service: OrganizationServiceDependency,
):
    return guard(lambda: service.invite(organization_id, user_id, payload))


@router.post("/{organization_id}/invitations/{invitation_id}/revoke", status_code=204)
def revoke(
    organization_id: int,
    invitation_id: int,
    user_id: CurrentUserId,
    service: OrganizationServiceDependency,
):
    guard(lambda: service.revoke_invitation(organization_id, user_id, invitation_id))
    return Response(status_code=204)


@router.post("/invitations/accept", response_model=OrganizationRead)
def accept_invitation(
    payload: InvitationAccept,
    user_id: CurrentUserId,
    service: OrganizationServiceDependency,
):
    return guard(lambda: service.accept_invitation(user_id, payload.token))


@router.get("/{organization_id}/activity", response_model=list[ActivityRead])
def activity(
    organization_id: int,
    user_id: CurrentUserId,
    service: OrganizationServiceDependency,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    return guard(lambda: service.activities(organization_id, user_id, offset, limit))


@router.get("/{organization_id}/projects", response_model=list[int])
def projects(organization_id: int, user_id: CurrentUserId, service: OrganizationServiceDependency):
    return guard(lambda: service.projects(organization_id, user_id))


@router.post("/{organization_id}/projects", response_model=list[int])
def link_project(
    organization_id: int,
    payload: ProjectLink,
    user_id: CurrentUserId,
    service: OrganizationServiceDependency,
):
    return guard(lambda: service.link_project(organization_id, user_id, payload.project_id))
