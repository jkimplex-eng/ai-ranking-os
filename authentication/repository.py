from datetime import datetime
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from authentication.models import AuthSession, AuthUser


class AuthenticationRepository(Protocol):
    def get_user_by_email(self, email: str) -> AuthUser | None: ...
    def get_user(self, user_id: int) -> AuthUser | None: ...
    def add_user(self, user: AuthUser) -> AuthUser: ...
    def add_session(self, session: AuthSession) -> AuthSession: ...
    def get_session(self, session_id: str) -> AuthSession | None: ...
    def revoke_session(
        self, session: AuthSession, at: datetime, replacement: str | None = None
    ) -> None: ...
    def revoke_family(self, family_id: str, at: datetime) -> None: ...


class SqlAlchemyAuthenticationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_email(self, email: str) -> AuthUser | None:
        return self.db.scalar(select(AuthUser).where(AuthUser.email == email.lower()))

    def get_user(self, user_id: int) -> AuthUser | None:
        return self.db.get(AuthUser, user_id)

    def add_user(self, user: AuthUser) -> AuthUser:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def add_session(self, session: AuthSession) -> AuthSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: str) -> AuthSession | None:
        return self.db.get(AuthSession, session_id)

    def revoke_session(
        self, session: AuthSession, at: datetime, replacement: str | None = None
    ) -> None:
        session.revoked_at = at
        session.replaced_by_session_id = replacement
        session.last_used_at = at
        self.db.commit()

    def revoke_family(self, family_id: str, at: datetime) -> None:
        self.db.execute(
            update(AuthSession)
            .where(AuthSession.family_id == family_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=at)
        )
        self.db.commit()
