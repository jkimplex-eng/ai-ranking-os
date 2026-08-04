from fastapi import FastAPI
from fastapi.testclient import TestClient

from authentication.middleware import ProductionAuthenticationMiddleware
from backend.app.config import Settings
from hardening.validation import validate_startup


def test_production_configuration_requires_auth_and_strong_jwt() -> None:
    errors = validate_startup(
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://user:pass@db/app",
            redis_url="redis://redis:6379/0",
            auth_jwt_secret="short",
            security_enforce_auth=False,
        )
    )
    assert "AUTH_JWT_SECRET must contain at least 32 bytes" in errors
    assert "SECURITY_ENFORCE_AUTH must be enabled in production" in errors


def test_production_authentication_perimeter_keeps_health_public() -> None:
    app = FastAPI()
    app.add_middleware(
        ProductionAuthenticationMiddleware,
        settings=Settings(security_enforce_auth=True),
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/protected")
    def protected():
        return {"status": "ok"}

    client = TestClient(app)
    assert client.get("/health").status_code == 200
    response = client.get("/protected")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
