from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from uuid import uuid4

import jwt

from authentication.models import AuthSession, AuthUser
from authentication.ports import AuthPrincipal, Clock, PasswordHasher, TokenCodec
from authentication.repository import AuthenticationRepository
from authentication.schemas import AuthUserRead, TokenPair


class AuthenticationError(ValueError):
    pass


class AuthenticationService:
    def __init__(
        self,
        repository: AuthenticationRepository,
        hasher: PasswordHasher,
        codec: TokenCodec,
        clock: Clock,
        *,
        access_minutes: int,
        refresh_days: int,
    ) -> None:
        self.repository = repository
        self.hasher = hasher
        self.codec = codec
        self.clock = clock
        self.access_minutes = access_minutes
        self.refresh_days = refresh_days

    def create_user(self, email: str, password: str, display_name: str) -> AuthUserRead:
        if self.repository.get_user_by_email(email) is not None:
            raise AuthenticationError("User already exists")
        user = self.repository.add_user(
            AuthUser(
                email=email.lower(),
                password_hash=self.hasher.hash(password),
                display_name=display_name,
            )
        )
        return AuthUserRead.model_validate(user)

    def login(self, email: str, password: str, ip: str | None, user_agent: str | None) -> TokenPair:
        user = self.repository.get_user_by_email(email)
        if (
            user is None
            or not user.is_active
            or not self.hasher.verify(user.password_hash, password)
        ):
            raise AuthenticationError("Invalid credentials")
        return self._issue(user, str(uuid4()), ip, user_agent)

    def refresh(self, token: str, ip: str | None, user_agent: str | None) -> TokenPair:
        claims = self._decode(token, "refresh")
        session = self.repository.get_session(str(claims["sid"]))
        now = self.clock.now()
        if session is None or not compare_digest(session.refresh_token_hash, self._hash(token)):
            raise AuthenticationError("Invalid refresh token")
        if session.revoked_at is not None:
            self.repository.revoke_family(session.family_id, now)
            raise AuthenticationError("Refresh token reuse detected")
        user = self.repository.get_user(int(claims["sub"]))
        if (
            user is None
            or not user.is_active
            or user.token_version != int(claims["ver"])
            or self._utc(session.expires_at) <= now
        ):
            raise AuthenticationError("Refresh token is no longer valid")
        replacement_id = str(uuid4())
        pair = self._issue(user, session.family_id, ip, user_agent, replacement_id)
        self.repository.revoke_session(session, now, replacement_id)
        return pair

    def logout(self, access_token: str, refresh_token: str | None = None) -> None:
        token = refresh_token or access_token
        expected = "refresh" if refresh_token else "access"
        claims = self._decode(token, expected)
        session = self.repository.get_session(str(claims["sid"]))
        if session is not None and session.revoked_at is None:
            self.repository.revoke_session(session, self.clock.now())

    def authenticate(self, access_token: str) -> AuthPrincipal:
        claims = self._decode(access_token, "access")
        user = self.repository.get_user(int(claims["sub"]))
        session = self.repository.get_session(str(claims["sid"]))
        now = self.clock.now()
        if (
            user is None
            or session is None
            or not user.is_active
            or session.revoked_at is not None
            or self._utc(session.expires_at) <= now
            or user.token_version != int(claims["ver"])
        ):
            raise AuthenticationError("Token is no longer valid")
        return AuthPrincipal(user.id, user.email, session.id, user.token_version)

    def me(self, access_token: str) -> AuthUserRead:
        principal = self.authenticate(access_token)
        user = self.repository.get_user(principal.user_id)
        if user is None:
            raise AuthenticationError("User not found")
        return AuthUserRead.model_validate(user)

    def _issue(
        self,
        user: AuthUser,
        family_id: str,
        ip: str | None,
        user_agent: str | None,
        session_id: str | None = None,
    ) -> TokenPair:
        now = self.clock.now()
        access_exp = now + timedelta(minutes=self.access_minutes)
        refresh_exp = now + timedelta(days=self.refresh_days)
        sid = session_id or str(uuid4())
        base = {"sub": str(user.id), "sid": sid, "ver": user.token_version, "iat": now}
        access = self.codec.encode(
            {**base, "jti": str(uuid4()), "typ": "access", "exp": access_exp}
        )
        refresh = self.codec.encode(
            {**base, "jti": str(uuid4()), "typ": "refresh", "exp": refresh_exp}
        )
        self.repository.add_session(
            AuthSession(
                id=sid,
                user_id=user.id,
                family_id=family_id,
                refresh_token_hash=self._hash(refresh),
                token_version=user.token_version,
                expires_at=refresh_exp,
                ip_address=ip,
                user_agent=user_agent,
            )
        )
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            access_expires_at=access_exp,
            refresh_expires_at=refresh_exp,
        )

    def _decode(self, token: str, expected_type: str) -> dict[str, object]:
        try:
            return self.codec.decode(token, expected_type)
        except jwt.PyJWTError as error:
            raise AuthenticationError("Invalid or expired token") from error

    @staticmethod
    def _hash(token: str) -> str:
        return sha256(token.encode()).hexdigest()

    @staticmethod
    def _utc(value: datetime) -> datetime:
        """Normalize SQLite's timezone-naive round-trip to UTC."""

        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
