"""Idempotently bootstrap the first production user from environment variables."""

from sqlalchemy import select

from authentication.dependencies import get_authentication_service
from authentication.repository import SqlAlchemyAuthenticationRepository
from backend.app.config import get_settings
from backend.app.database import SessionLocal
from rbac.models import Role, UserRole


def ensure_superadmin(db, user_id: int) -> None:
    role = db.scalar(select(Role).where(Role.code == "superadmin"))
    if role is None:
        role = Role(
            code="superadmin",
            name="SuperAdmin",
            description="Production system administrator",
            is_system=True,
        )
        db.add(role)
        db.flush()
    assignment = db.get(UserRole, (user_id, role.id))
    if assignment is None:
        db.add(UserRole(user_id=user_id, role_id=role.id))
    db.commit()


def main() -> None:
    settings = get_settings()
    if not settings.admin_email or not settings.admin_password:
        print("Admin bootstrap skipped: ADMIN_EMAIL/ADMIN_PASSWORD are not configured")
        return
    with SessionLocal() as db:
        repository = SqlAlchemyAuthenticationRepository(db)
        user = repository.get_user_by_email(settings.admin_email)
        if user is None:
            user = get_authentication_service(db).create_user(
                settings.admin_email,
                settings.admin_password,
                settings.admin_display_name,
            )
            print("Admin user created")
        ensure_superadmin(db, user.id)
        print("Admin RBAC role is ready")


if __name__ == "__main__":
    main()
