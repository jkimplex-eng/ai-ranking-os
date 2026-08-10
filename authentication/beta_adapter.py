from sqlalchemy import func, select
from sqlalchemy.orm import Session

from authentication.models import AuthSession, AuthUser
from authentication.repository import SqlAlchemyAuthenticationRepository
from authentication.security import Argon2PasswordHasher
from closed_beta.ports import BetaUserFacts


class AuthenticationBetaIdentity:
    def __init__(self, db: Session) -> None:
        self.db = db

    def users(self) -> list[BetaUserFacts]:
        last_seen = dict(
            self.db.execute(
                select(
                    AuthSession.user_id,
                    func.max(func.coalesce(AuthSession.last_used_at, AuthSession.created_at)),
                ).group_by(AuthSession.user_id)
            ).all()
        )
        return [
            BetaUserFacts(
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
                is_active=user.is_active,
                registered_at=user.created_at,
                last_seen_at=last_seen.get(user.id),
            )
            for user in self.db.scalars(select(AuthUser).order_by(AuthUser.created_at.desc()))
        ]

    def exists(self, email: str) -> bool:
        return (
            SqlAlchemyAuthenticationRepository(self.db).get_user_by_email(email.lower())
            is not None
        )

    def create(self, email: str, password: str, display_name: str) -> int:
        repository = SqlAlchemyAuthenticationRepository(self.db)
        user = repository.add_user(
            AuthUser(
                email=email.lower(),
                password_hash=Argon2PasswordHasher().hash(password),
                display_name=display_name,
            )
        )
        return user.id
