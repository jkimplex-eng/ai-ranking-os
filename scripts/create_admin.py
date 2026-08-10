"""Idempotently bootstrap the first production user from environment variables."""

from authentication.dependencies import get_authentication_service
from authentication.repository import SqlAlchemyAuthenticationRepository
from backend.app.config import get_settings
from backend.app.database import SessionLocal


def main() -> None:
    settings = get_settings()
    if not settings.admin_email or not settings.admin_password:
        print("Admin bootstrap skipped: ADMIN_EMAIL/ADMIN_PASSWORD are not configured")
        return
    with SessionLocal() as db:
        repository = SqlAlchemyAuthenticationRepository(db)
        if repository.get_user_by_email(settings.admin_email) is not None:
            print("Admin bootstrap skipped: user already exists")
            return
        service = get_authentication_service(db)
        service.create_user(
            settings.admin_email,
            settings.admin_password,
            settings.admin_display_name,
        )
        print("Admin user created")


if __name__ == "__main__":
    main()
