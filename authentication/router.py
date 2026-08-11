from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from authentication.dependencies import AuthServiceDependency, require_token
from authentication.schemas import (
    AuthUserRead,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
)
from authentication.service import AuthenticationError
from backend.app.database import get_db
from rate_limit.backend import MemoryRateLimitBackend
from rbac.models import Role, UserRole

router = APIRouter(prefix="/auth", tags=["authentication"])
AccessToken = Annotated[str, Depends(require_token)]
_login_limiter = MemoryRateLimitBackend()


def _client(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    return ip, request.headers.get("user-agent")


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, request: Request, service: AuthServiceDependency) -> TokenPair:
    client_ip = request.client.host if request.client else "unknown"
    decision = _login_limiter.token_bucket(f"auth-login:{client_ip}", 10, 60, burst=5)
    if not decision.allowed:
        retry_after = max(1, int(decision.retry_after_seconds + 0.999))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
            headers={"Retry-After": str(retry_after)},
        )
    try:
        return service.login(payload.email, payload.password, *_client(request))
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, request: Request, service: AuthServiceDependency) -> TokenPair:
    try:
        return service.refresh(payload.refresh_token, *_client(request))
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    service: AuthServiceDependency,
    access_token: AccessToken,
) -> Response:
    try:
        service.logout(access_token, payload.refresh_token)
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=AuthUserRead)
def me(
    service: AuthServiceDependency,
    access_token: AccessToken,
    db: Annotated[Session, Depends(get_db)],
) -> AuthUserRead:
    try:
        user = service.me(access_token)
        roles = list(
            db.scalars(
                select(Role.code)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user.id)
            )
        )
        return AuthUserRead.model_validate(user).model_copy(update={"roles": roles})
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
