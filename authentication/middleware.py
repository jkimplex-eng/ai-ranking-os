from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from apikeys.repository import ApiKeyRepository
from apikeys.service import ApiKeyError, ApiKeyService
from authentication.repository import SqlAlchemyAuthenticationRepository
from authentication.security import Argon2PasswordHasher, JwtTokenCodec, UtcClock
from authentication.service import AuthenticationError, AuthenticationService
from backend.app.config import Settings
from backend.app.database import SessionLocal

PUBLIC_PATHS = {
    "/health",
    "/live",
    "/ready",
    "/version",
    "/metrics",
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/auth/login",
    "/auth/refresh",
    "/observability/health",
    "/observability/liveness",
    "/observability/readiness",
}


class ProductionAuthenticationMiddleware(BaseHTTPMiddleware):
    """Authenticate production requests without changing route contracts."""

    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        if (
            not self.settings.security_enforce_auth
            or request.url.path in PUBLIC_PATHS
            or request.url.path.startswith("/shared/reports/")
        ):
            return await call_next(request)
        with SessionLocal() as db:
            api_key = request.headers.get("x-api-key")
            if api_key:
                try:
                    request.state.principal = ApiKeyService(ApiKeyRepository(db)).validate(api_key)
                    return await call_next(request)
                except ApiKeyError:
                    return self._unauthorized()
            authorization = request.headers.get("authorization", "")
            if not authorization.lower().startswith("bearer "):
                return self._unauthorized()
            service = AuthenticationService(
                SqlAlchemyAuthenticationRepository(db),
                Argon2PasswordHasher(),
                JwtTokenCodec(
                    self.settings.auth_jwt_secret,
                    self.settings.auth_jwt_algorithm,
                    self.settings.auth_jwt_issuer,
                    self.settings.auth_jwt_audience,
                ),
                UtcClock(),
                access_minutes=self.settings.auth_access_token_minutes,
                refresh_days=self.settings.auth_refresh_token_days,
            )
            try:
                request.state.principal = service.authenticate(authorization[7:])
            except AuthenticationError:
                return self._unauthorized()
        return await call_next(request)

    @staticmethod
    def _unauthorized() -> JSONResponse:
        return JSONResponse(
            {"detail": "Authentication required"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )
