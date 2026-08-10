from sqlalchemy import func, select
from sqlalchemy.orm import Session

from report_sharing.models import ReportShareLink, ReportShareView


class ShareRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, link: ReportShareLink) -> ReportShareLink:
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def get(self, share_id: int) -> ReportShareLink | None:
        return self.db.get(ReportShareLink, share_id)

    def by_token_hash(self, token_hash: str) -> ReportShareLink | None:
        return self.db.scalar(
            select(ReportShareLink).where(ReportShareLink.token_hash == token_hash)
        )

    def list(self, research_id: int) -> list[ReportShareLink]:
        return list(
            self.db.scalars(
                select(ReportShareLink)
                .where(ReportShareLink.research_id == research_id)
                .order_by(ReportShareLink.created_at.desc())
            )
        )

    def view_count(self, share_id: int) -> int:
        return int(
            self.db.scalar(
                select(func.count(ReportShareView.id)).where(
                    ReportShareView.share_id == share_id
                )
            )
            or 0
        )

    def add_view(self, view: ReportShareView) -> None:
        self.db.add(view)
        self.db.commit()
