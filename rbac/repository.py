from typing import Protocol

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from rbac.models import Permission, Role, UserRole, role_inheritance, role_permissions


class RbacRepository(Protocol):
    def list_roles(self) -> list[Role]: ...
    def get_role(self, role_id: int) -> Role | None: ...
    def get_role_by_code(self, code: str) -> Role | None: ...
    def save_role(self, role: Role) -> Role: ...
    def delete_role(self, role: Role) -> None: ...
    def list_permissions(self) -> list[Permission]: ...
    def get_permission(self, permission_id: int) -> Permission | None: ...
    def save_permission(self, permission: Permission) -> Permission: ...
    def delete_permission(self, permission: Permission) -> None: ...


class SqlAlchemyRbacRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_roles(self) -> list[Role]:
        return list(self.db.scalars(select(Role).order_by(Role.id)))

    def get_role(self, role_id: int) -> Role | None:
        return self.db.get(Role, role_id)

    def get_role_by_code(self, code: str) -> Role | None:
        return self.db.scalar(select(Role).where(Role.code == code))

    def save_role(self, role: Role) -> Role:
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def delete_role(self, role: Role) -> None:
        self.db.delete(role)
        self.db.commit()

    def list_permissions(self) -> list[Permission]:
        return list(self.db.scalars(select(Permission).order_by(Permission.id)))

    def get_permission(self, permission_id: int) -> Permission | None:
        return self.db.get(Permission, permission_id)

    def save_permission(self, permission: Permission) -> Permission:
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def delete_permission(self, permission: Permission) -> None:
        self.db.delete(permission)
        self.db.commit()

    def parent_ids(self, role_id: int) -> list[int]:
        return list(
            self.db.scalars(
                select(role_inheritance.c.parent_role_id).where(
                    role_inheritance.c.role_id == role_id
                )
            )
        )

    def set_parents(self, role_id: int, parent_ids: list[int]) -> None:
        self.db.execute(delete(role_inheritance).where(role_inheritance.c.role_id == role_id))
        if parent_ids:
            self.db.execute(
                insert(role_inheritance),
                [{"role_id": role_id, "parent_role_id": value} for value in parent_ids],
            )
        self.db.commit()

    def permission_ids(self, role_id: int) -> list[int]:
        return list(
            self.db.scalars(
                select(role_permissions.c.permission_id).where(
                    role_permissions.c.role_id == role_id
                )
            )
        )

    def add_permission(self, role_id: int, permission_id: int) -> None:
        if permission_id not in self.permission_ids(role_id):
            self.db.execute(
                insert(role_permissions).values(role_id=role_id, permission_id=permission_id)
            )
            self.db.commit()

    def remove_permission(self, role_id: int, permission_id: int) -> None:
        self.db.execute(
            delete(role_permissions).where(
                role_permissions.c.role_id == role_id,
                role_permissions.c.permission_id == permission_id,
            )
        )
        self.db.commit()

    def user_role_ids(self, user_id: int) -> list[int]:
        return list(self.db.scalars(select(UserRole.role_id).where(UserRole.user_id == user_id)))

    def assign_role(self, user_id: int, role_id: int) -> None:
        if role_id not in self.user_role_ids(user_id):
            self.db.add(UserRole(user_id=user_id, role_id=role_id))
            self.db.commit()

    def unassign_role(self, user_id: int, role_id: int) -> None:
        self.db.execute(
            delete(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        )
        self.db.commit()
