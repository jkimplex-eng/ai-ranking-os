from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from backend.app.database import get_db
from closed_beta.dependencies import require_beta_admin
from rbac.repository import SqlAlchemyRbacRepository
from rbac.schemas import (
    AccessCheck,
    AccessDecision,
    PermissionCreate,
    PermissionRead,
    RoleCreate,
    RolePermissionChange,
    RoleRead,
    RoleUpdate,
    UserRoleAssignment,
)
from rbac.service import RbacError, RbacNotFoundError, RbacService

router = APIRouter(prefix="/rbac", tags=["rbac"], dependencies=[Depends(require_beta_admin)])


def get_rbac_service(db: Annotated[Session, Depends(get_db)]) -> RbacService:
    return RbacService(SqlAlchemyRbacRepository(db))


Service = Annotated[RbacService, Depends(get_rbac_service)]


def guard(call):
    try:
        return call()
    except RbacNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except RbacError as error:
        raise HTTPException(409, str(error)) from error


@router.post("/roles", response_model=RoleRead, status_code=201)
def create_role(payload: RoleCreate, service: Service):
    return guard(lambda: service.create_role(payload))


@router.get("/roles", response_model=list[RoleRead])
def list_roles(service: Service):
    return service.list_roles()


@router.patch("/roles/{role_id}", response_model=RoleRead)
def update_role(role_id: int, payload: RoleUpdate, service: Service):
    return guard(lambda: service.update_role(role_id, payload))


@router.delete("/roles/{role_id}", status_code=204)
def delete_role(role_id: int, service: Service):
    guard(lambda: service.delete_role(role_id))
    return Response(status_code=204)


@router.post("/permissions", response_model=PermissionRead, status_code=201)
def create_permission(payload: PermissionCreate, service: Service):
    return guard(lambda: service.create_permission(payload))


@router.get("/permissions", response_model=list[PermissionRead])
def list_permissions(service: Service):
    return service.list_permissions()


@router.delete("/permissions/{permission_id}", status_code=204)
def delete_permission(permission_id: int, service: Service):
    guard(lambda: service.delete_permission(permission_id))
    return Response(status_code=204)


@router.post("/roles/{role_id}/permissions", response_model=RoleRead)
def grant(role_id: int, payload: RolePermissionChange, service: Service):
    return guard(lambda: service.grant(role_id, payload.permission_id))


@router.delete("/roles/{role_id}/permissions/{permission_id}", response_model=RoleRead)
def revoke(role_id: int, permission_id: int, service: Service):
    return guard(lambda: service.revoke(role_id, permission_id))


@router.post("/users/{user_id}/roles", response_model=list[int])
def assign(user_id: int, payload: UserRoleAssignment, service: Service):
    return guard(lambda: service.assign(user_id, payload.role_id))


@router.delete("/users/{user_id}/roles/{role_id}", response_model=list[int])
def unassign(user_id: int, role_id: int, service: Service):
    return service.unassign(user_id, role_id)


@router.post("/check", response_model=AccessDecision)
def check(payload: AccessCheck, service: Service):
    return service.check(payload.user_id, payload.resource, payload.action, payload.scope)
