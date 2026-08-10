from sqlalchemy import select
from sqlalchemy.orm import Session

from closed_beta.ports import RolePort
from rbac.models import Role, UserRole
from rbac.repository import SqlAlchemyRbacRepository


class RbacBetaRoles(RolePort):
    ADMIN_CODES = {"superadmin", "admin", "SUPERADMIN", "ADMIN"}

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = SqlAlchemyRbacRepository(db)

    def assign(self, user_id: int, role_id: int) -> None:
        if self.repository.get_role(role_id) is None:
            raise ValueError("Role not found")
        self.repository.assign_role(user_id, role_id)

    def is_admin(self, user_id: int) -> bool:
        codes = set(
            self.db.scalars(
                select(Role.code)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id)
            )
        )
        return bool(codes & self.ADMIN_CODES)
