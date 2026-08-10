import csv
import hashlib
import io
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from openpyxl import Workbook

from product_analytics.engine import ProductAnalyticsEngine
from product_analytics.models import AnalyticsEvent, AnalyticsReport, AnalyticsSession
from product_analytics.repository import ProductAnalyticsRepository
from product_analytics.schemas import (
    AnalyticsFilters,
    AnalyticsPeriod,
    DashboardRead,
    EventCreate,
    EventRead,
    SessionRead,
    SessionStart,
)


class ProductAnalyticsError(ValueError):
    pass


class ProductAnalyticsService:
    CACHE_TTL = timedelta(minutes=5)
    PERIOD_RANGES = {
        AnalyticsPeriod.HOURLY: timedelta(days=7),
        AnalyticsPeriod.DAILY: timedelta(days=30),
        AnalyticsPeriod.WEEKLY: timedelta(days=180),
        AnalyticsPeriod.MONTHLY: timedelta(days=365),
    }

    def __init__(self, repository: ProductAnalyticsRepository) -> None:
        self.repository = repository
        self.engine = ProductAnalyticsEngine()

    def record(self, payload: EventCreate) -> EventRead:
        return self.record_batch([payload])[0]

    def record_batch(self, payloads: list[EventCreate]) -> list[EventRead]:
        rows = self.repository.add_events(
            [
                AnalyticsEvent(
                    organization_id=item.organization_id,
                    user_id=item.user_id,
                    session_id=item.session_id,
                    event_name=item.event_name.upper().replace(" ", "_"),
                    event_category=item.event_category.value,
                    entity_type=item.entity_type,
                    entity_id=item.entity_id,
                    metadata_payload=item.metadata,
                    ip_hash=item.ip_hash,
                    user_agent=item.user_agent,
                    **({"created_at": item.created_at} if item.created_at else {}),
                )
                for item in payloads
            ]
        )
        return [self._event_read(row) for row in rows]

    @staticmethod
    def _event_read(row: AnalyticsEvent) -> EventRead:
        return EventRead(
            id=row.id,
            organization_id=row.organization_id,
            user_id=row.user_id,
            session_id=row.session_id,
            event_name=row.event_name,
            event_category=row.event_category,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            metadata=row.metadata_payload,
            ip_hash=row.ip_hash,
            user_agent=row.user_agent,
            created_at=row.created_at,
        )

    def start_session(self, user_id: int | None, payload: SessionStart) -> SessionRead:
        now = datetime.now(UTC)
        row = self.repository.save_session(
            AnalyticsSession(
                id=str(uuid4()),
                user_id=user_id,
                organization_id=payload.organization_id,
                started_at=now,
                device=payload.device,
                browser=payload.browser,
                os=payload.os,
            )
        )
        return SessionRead.model_validate(row, from_attributes=True)

    def finish_session(self, session_id: str, user_id: int) -> SessionRead:
        row = self.repository.session(session_id)
        if row is None:
            raise ProductAnalyticsError("Analytics session not found")
        if row.user_id is not None and row.user_id != user_id:
            raise ProductAnalyticsError("Analytics session not found")
        if row.finished_at is None:
            now = datetime.now(UTC)
            started = row.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=UTC)
            row.finished_at = now
            row.duration = round((now - started).total_seconds(), 3)
            self.repository.save_session(row)
        return SessionRead.model_validate(row, from_attributes=True)

    def list_events(self, offset: int, limit: int) -> list[EventRead]:
        return [self._event_read(row) for row in self.repository.event_page(offset, limit)]

    @staticmethod
    def _filter_hash(filters: AnalyticsFilters) -> str:
        value = json.dumps(filters.model_dump(mode="json"), sort_keys=True)
        return hashlib.sha256(value.encode()).hexdigest()

    def dashboard(
        self,
        period: AnalyticsPeriod,
        filters: AnalyticsFilters,
        *,
        force: bool = False,
    ) -> DashboardRead:
        now = datetime.now(UTC)
        end = filters.date_to or now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        start = filters.date_from or end - self.PERIOD_RANGES[period]
        effective = filters.model_copy(update={"date_from": start, "date_to": end})
        filters_hash = self._filter_hash(effective)
        if not force:
            cached = self.repository.latest_report(
                period.value, filters_hash, now - self.CACHE_TTL
            )
            if cached is not None:
                return DashboardRead.model_validate(cached.payload).model_copy(
                    update={"cached": True}
                )
        events = self.repository.events(effective)
        sessions = self.repository.sessions(effective)
        report = self.engine.build(events, sessions, period, start, end)
        self.repository.save_report(
            AnalyticsReport(
                period=period.value,
                filters_hash=filters_hash,
                range_start=start,
                range_end=end,
                payload=report.model_dump(mode="json"),
                event_count=len(events),
            )
        )
        return report

    def export(
        self, format_name: str, period: AnalyticsPeriod, filters: AnalyticsFilters
    ) -> tuple[bytes, str, str]:
        report = self.dashboard(period, filters)
        payload = report.model_dump(mode="json")
        if format_name == "json":
            return (
                json.dumps(payload, ensure_ascii=False, indent=2).encode(),
                "application/json",
                "product-analytics.json",
            )
        rows = self._flat_rows(payload)
        if format_name == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["section", "metric", "value"])
            writer.writerows(rows)
            return output.getvalue().encode("utf-8-sig"), "text/csv", "product-analytics.csv"
        if format_name == "xlsx":
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Product Analytics"
            sheet.append(["Section", "Metric", "Value"])
            for row in rows:
                sheet.append(row)
            buffer = io.BytesIO()
            workbook.save(buffer)
            return (
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "product-analytics.xlsx",
            )
        raise ProductAnalyticsError("Unsupported export format")

    @staticmethod
    def _flat_rows(payload: dict) -> list[list[str]]:
        rows = []
        for section, values in payload.items():
            if isinstance(values, dict):
                for metric, value in values.items():
                    rows.append([section, metric, json.dumps(value, ensure_ascii=False)])
        return rows
