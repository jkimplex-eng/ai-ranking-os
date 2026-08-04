from backend.app.config import Settings


def validate_startup(settings: Settings) -> list[str]:
    errors = []
    if (
        settings.app_env.lower() in {"production", "prod"}
        and settings.auth_jwt_secret == "development-only-change-me"
    ):
        errors.append("AUTH_JWT_SECRET must be replaced in production")
    if not settings.database_url.startswith(("postgresql+psycopg://", "sqlite")):
        errors.append("Unsupported database URL")
    if not settings.redis_url.startswith(("redis://", "rediss://")):
        errors.append("Unsupported Redis URL")
    return errors
