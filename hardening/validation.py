from backend.app.config import Settings, get_settings


def validate_startup(settings: Settings) -> list[str]:
    errors = []
    if (
        settings.app_env.lower() in {"production", "prod"}
        and settings.auth_jwt_secret == "development-only-change-me"
    ):
        errors.append("AUTH_JWT_SECRET must be replaced in production")
    if settings.app_env.lower() in {"production", "prod"}:
        if len(settings.auth_jwt_secret.encode()) < 32:
            errors.append("AUTH_JWT_SECRET must contain at least 32 bytes")
        if settings.auth_jwt_algorithm not in {"HS256", "HS384", "HS512"}:
            errors.append("AUTH_JWT_ALGORITHM must be HS256, HS384, or HS512")
        if not settings.security_enforce_auth:
            errors.append("SECURITY_ENFORCE_AUTH must be enabled in production")
    if not settings.database_url.startswith(("postgresql+psycopg://", "sqlite")):
        errors.append("Unsupported database URL")
    if not settings.redis_url.startswith(("redis://", "rediss://")):
        errors.append("Unsupported Redis URL")
    return errors


def main() -> None:
    errors = validate_startup(get_settings())
    if errors:
        raise SystemExit("Startup validation failed: " + "; ".join(errors))


if __name__ == "__main__":
    main()
