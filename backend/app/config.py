from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_version: str = "1.0.0"
    database_url: str = Field(
        default="postgresql+psycopg://ai_ranking:ai_ranking@localhost:5432/ai_ranking"
    )
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    execution_retry_base_seconds: float = Field(default=0.1, ge=0)
    build_sha: str = "development"
    release_channel: str = "production"
    auth_jwt_secret: str = "development-only-change-me"
    auth_jwt_algorithm: str = "HS256"
    auth_jwt_issuer: str = "ai-ranking-os"
    auth_jwt_audience: str = "ai-ranking-os-api"
    auth_access_token_minutes: int = Field(default=15, ge=1, le=1440)
    auth_refresh_token_days: int = Field(default=30, ge=1, le=365)
    request_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    max_inflight_requests: int = Field(default=500, ge=1)
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=200)
    database_pool_timeout_seconds: int = Field(default=30, ge=1, le=300)
    database_pool_recycle_seconds: int = Field(default=1800, ge=30, le=86400)
    graceful_shutdown_seconds: int = Field(default=30, ge=1, le=300)
    security_enforce_auth: bool = False
    admin_email: str | None = None
    admin_password: str | None = None
    admin_display_name: str = "AI Ranking OS Administrator"
    provider_secret_key: str | None = None
    yandex_webmaster_client_id: str | None = None
    yandex_webmaster_client_secret: str | None = None
    yandex_webmaster_redirect_uri: str = (
        "https://app.разуммаркета.рф/api/integrations/yandex-webmaster/callback"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
