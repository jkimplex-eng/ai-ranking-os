from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from authentication.ports import AuthPrincipal
from authentication.repository import SqlAlchemyAuthenticationRepository
from authentication.security import Argon2PasswordHasher, JwtTokenCodec, UtcClock
from authentication.service import AuthenticationError, AuthenticationService
from backend.app.config import get_settings
from backend.app.database import get_db

bearer = HTTPBearer(auto_error=False)


def get_authentication_service(db: Annotated[Session, Depends(get_db)]) -> AuthenticationService:
    settings = get_settings()
    return AuthenticationService(
        SqlAlchemyAuthenticationRepository(db),
        Argon2PasswordHasher(),
        JwtTokenCodec(
            secret=settings.auth_jwt_secret,
            algorithm=settings.auth_jwt_algorithm,
            issuer=settings.auth_jwt_issuer,
            audience=settings.auth_jwt_audience,
        ),
        UtcClock(),
        access_minutes=settings.auth_access_token_minutes,
        refresh_days=settings.auth_refresh_token_days,
    )


AuthServiceDependency = Annotated[AuthenticationService, Depends(get_authentication_service)]
CredentialsDependency = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def require_token(credentials: CredentialsDependency) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return credentials.credentials


def get_current_principal(
    service: AuthServiceDependency, token: Annotated[str, Depends(require_token)]
) -> AuthPrincipal:
    try:
        return service.authenticate(token)
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error


CurrentPrincipal = Annotated[AuthPrincipal, Depends(get_current_principal)]
