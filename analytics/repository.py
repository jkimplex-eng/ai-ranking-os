from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from analytics.models import AnalyticsRun


class AnalyticsRunNotFoundError(LookupError):
    """Requested analytics run does not exist."""


class AnalyticsRepository(Protocol):
    def create(
        self,
        *,
        engine_version: str,
        query_payload: dict[str, Any],
        result_payload: dict[str, Any],
        source_record_count: int,
        group_count: int,
    ) -> AnalyticsRun: ...

    def get(self, run_id: int) -> AnalyticsRun: ...

    def list(self, page: int, page_size: int) -> tuple[list[AnalyticsRun], int]: ...


class SqlAlchemyAnalyticsRepository(AnalyticsRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        engine_version: str,
        query_payload: dict[str, Any],
        result_payload: dict[str, Any],
        source_record_count: int,
        group_count: int,
    ) -> AnalyticsRun:
        run = AnalyticsRun(
            engine_version=engine_version,
            query_payload=query_payload,
            result_payload=result_payload,
            source_record_count=source_record_count,
            group_count=group_count,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get(self, run_id: int) -> AnalyticsRun:
        run = self.db.get(AnalyticsRun, run_id)
        if run is None:
            raise AnalyticsRunNotFoundError(f"Analytics run {run_id} not found")
        return run

    def list(self, page: int, page_size: int) -> tuple[list[AnalyticsRun], int]:
        total = self.db.scalar(select(func.count(AnalyticsRun.id))) or 0
        rows = self.db.scalars(
            select(AnalyticsRun)
            .order_by(AnalyticsRun.calculated_at.desc(), AnalyticsRun.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(rows), total
