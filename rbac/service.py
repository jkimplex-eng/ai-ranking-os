from rbac.models import Permission, Role
from rbac.repository import SqlAlchemyRbacRepository
from rbac.schemas import (
    AccessDecision,
    PermissionCreate,
    PermissionRead,
    RoleCreate,
    RoleRead,
    RoleUpdate,
)


class RbacError(ValueError):
    pass


class RbacNotFoundError(LookupError):
    pass


class RbacService:
    def __init__(self, repository: SqlAlchemyRbacRepository) -> None:
        self.repository = repository

    def create_role(self, data: RoleCreate) -> RoleRead:
        if self.repository.get_role_by_code(data.code):
            raise RbacError("Role code already exists")
        role = self.repository.save_role(
            Role(code=data.code, name=data.name, description=data.description)
        )
        self._validate_parents(role.id, data.parent_role_ids)
        self.repository.set_parents(role.id, data.parent_role_ids)
        return self._role_read(role)

    def list_roles(self) -> list[RoleRead]:
        return [self._role_read(value) for value in self.repository.list_roles()]

    def update_role(self, role_id: int, data: RoleUpdate) -> RoleRead:
        role = self._role(role_id)
        if role.is_system and data.parent_role_ids is not None:
            raise RbacError("System role hierarchy is immutable")
        for field, value in data.model_dump(exclude_none=True, exclude={"parent_role_ids"}).items():
            setattr(role, field, value)
        self.repository.save_role(role)
        if data.parent_role_ids is not None:
            self._validate_parents(role_id, data.parent_role_ids)
            self.repository.set_parents(role_id, data.parent_role_ids)
        return self._role_read(role)

    def delete_role(self, role_id: int) -> None:
        role = self._role(role_id)
        if role.is_system:
            raise RbacError("System roles cannot be deleted")
        self.repository.delete_role(role)

    def create_permission(self, data: PermissionCreate) -> PermissionRead:
        try:
            return PermissionRead.model_validate(
                self.repository.save_permission(Permission(**data.model_dump()))
            )
        except Exception as error:
            raise RbacError("Permission already exists") from error

    def list_permissions(self) -> list[PermissionRead]:
        return [
            PermissionRead.model_validate(value) for value in self.repository.list_permissions()
        ]

    def delete_permission(self, permission_id: int) -> None:
        permission = self.repository.get_permission(permission_id)
        if not permission:
            raise RbacNotFoundError("Permission not found")
        self.repository.delete_permission(permission)

    def grant(self, role_id: int, permission_id: int) -> RoleRead:
        role = self._role(role_id)
        if not self.repository.get_permission(permission_id):
            raise RbacNotFoundError("Permission not found")
        self.repository.add_permission(role_id, permission_id)
        return self._role_read(role)

    def revoke(self, role_id: int, permission_id: int) -> RoleRead:
        role = self._role(role_id)
        self.repository.remove_permission(role_id, permission_id)
        return self._role_read(role)

    def assign(self, user_id: int, role_id: int) -> list[int]:
        self._role(role_id)
        self.repository.assign_role(user_id, role_id)
        return self.repository.user_role_ids(user_id)

    def unassign(self, user_id: int, role_id: int) -> list[int]:
        self.repository.unassign_role(user_id, role_id)
        return self.repository.user_role_ids(user_id)

    def is_allowed(self, user_id: int, resource: str, action: str, scope: str = "global") -> bool:
        effective = self._effective(self.repository.user_role_ids(user_id))
        for role_id in effective:
            for permission_id in self.repository.permission_ids(role_id):
                permission = self.repository.get_permission(permission_id)
                if (
                    permission
                    and permission.resource in {resource, "*"}
                    and permission.action in {action, "*"}
                    and permission.scope in {scope, "*"}
                ):
                    return True
        return False

    def check(self, user_id: int, resource: str, action: str, scope: str) -> AccessDecision:
        effective = sorted(self._effective(self.repository.user_role_ids(user_id)))
        return AccessDecision(
            allowed=self.is_allowed(user_id, resource, action, scope), effective_role_ids=effective
        )

    def _effective(self, roots: list[int]) -> set[int]:
        result, pending = set(), list(roots)
        while pending:
            current = pending.pop()
            if current not in result:
                result.add(current)
                pending.extend(self.repository.parent_ids(current))
        return result

    def _validate_parents(self, role_id: int, parents: list[int]) -> None:
        if role_id in parents:
            raise RbacError("Role cannot inherit itself")
        for parent in parents:
            self._role(parent)
            if role_id in self._effective([parent]):
                raise RbacError("Role inheritance cycle")

    def _role(self, role_id: int) -> Role:
        role = self.repository.get_role(role_id)
        if not role:
            raise RbacNotFoundError("Role not found")
        return role

    def _role_read(self, role: Role) -> RoleRead:
        return RoleRead.model_validate(
            {
                **role.__dict__,
                "parent_role_ids": self.repository.parent_ids(role.id),
                "permission_ids": self.repository.permission_ids(role.id),
            }
        )
