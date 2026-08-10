from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_analytics.models import AnalyticsEvent, AnalyticsReport, AnalyticsSession
from product_analytics.schemas import AnalyticsFilters


class ProductAnalyticsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_events(self, events: list[AnalyticsEvent]) -> list[AnalyticsEvent]:
        self.db.add_all(events)
        self.db.commit()
        for event in events:
            self.db.refresh(event)
        return events

    def events(self, filters: AnalyticsFilters) -> list[AnalyticsEvent]:
        statement = select(AnalyticsEvent)
        if filters.organization_id is not None:
            statement = statement.where(
                AnalyticsEvent.organization_id == filters.organization_id
            )
        if filters.user_id is not None:
            statement = statement.where(AnalyticsEvent.user_id == filters.user_id)
        if filters.date_from is not None:
            statement = statement.where(AnalyticsEvent.created_at >= filters.date_from)
        if filters.date_to is not None:
            statement = statement.where(AnalyticsEvent.created_at <= filters.date_to)
        rows = list(self.db.scalars(statement.order_by(AnalyticsEvent.created_at)))
        metadata_filters = {
            "provider": filters.provider,
            "template": filters.template,
            "region": filters.region,
            "language": filters.language,
        }
        return [
            row
            for row in rows
            if all(
                value is None
                or row.metadata_payload.get(key) == value
                or value in row.metadata_payload.get(f"{key}s", [])
                for key, value in metadata_filters.items()
            )
        ]

    def event_page(self, offset: int, limit: int) -> list[AnalyticsEvent]:
        statement = (
            select(AnalyticsEvent)
            .order_by(AnalyticsEvent.created_at.desc(), AnalyticsEvent.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(statement))

    def sessions(self, filters: AnalyticsFilters) -> list[AnalyticsSession]:
        statement = select(AnalyticsSession)
        if filters.organization_id is not None:
            statement = statement.where(
                AnalyticsSession.organization_id == filters.organization_id
            )
        if filters.user_id is not None:
            statement = statement.where(AnalyticsSession.user_id == filters.user_id)
        if filters.date_from is not None:
            statement = statement.where(AnalyticsSession.started_at >= filters.date_from)
        if filters.date_to is not None:
            statement = statement.where(AnalyticsSession.started_at <= filters.date_to)
        return list(self.db.scalars(statement.order_by(AnalyticsSession.started_at)))

    def save_session(self, session: AnalyticsSession) -> AnalyticsSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def session(self, session_id: str) -> AnalyticsSession | None:
        return self.db.get(AnalyticsSession, session_id)

    def save_report(self, report: AnalyticsReport) -> AnalyticsReport:
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def latest_report(
        self, period: str, filters_hash: str, after: datetime
    ) -> AnalyticsReport | None:
        return self.db.scalar(
            select(AnalyticsReport)
            .where(
                AnalyticsReport.period == period,
                AnalyticsReport.filters_hash == filters_hash,
                AnalyticsReport.created_at >= after,
            )
            .order_by(AnalyticsReport.created_at.desc())
        )
