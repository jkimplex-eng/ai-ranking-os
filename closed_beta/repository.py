from sqlalchemy import select
from sqlalchemy.orm import Session

from closed_beta.models import BetaInvitation, BetaUserProfile


class BetaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def profiles(self, user_ids: list[int]) -> dict[int, BetaUserProfile]:
        if not user_ids:
            return {}
        return {
            item.user_id: item
            for item in self.db.scalars(
                select(BetaUserProfile).where(BetaUserProfile.user_id.in_(user_ids))
            )
        }

    def profile(self, user_id: int) -> BetaUserProfile | None:
        return self.db.scalar(
            select(BetaUserProfile).where(BetaUserProfile.user_id == user_id)
        )

    def save_profile(self, item: BetaUserProfile) -> BetaUserProfile:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def save_invitation(self, item: BetaInvitation) -> BetaInvitation:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def invitation(self, invitation_id: int) -> BetaInvitation | None:
        return self.db.get(BetaInvitation, invitation_id)

    def invitation_by_hash(self, token_hash: str) -> BetaInvitation | None:
        return self.db.scalar(
            select(BetaInvitation).where(BetaInvitation.token_hash == token_hash)
        )

    def invitations(self) -> list[BetaInvitation]:
        return list(
            self.db.scalars(
                select(BetaInvitation).order_by(BetaInvitation.created_at.desc())
            )
        )
