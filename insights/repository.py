from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from insights.models import Insight, InsightRun
from insights.schemas import InsightRequest


class InsightRunNotFoundError(LookupError):
    pass


class InsightRepository(Protocol):
    def create(
        self, request: InsightRequest, source_count: int, insights: list[dict[str, Any]]
    ) -> InsightRun: ...
    def get(self, run_id: int) -> InsightRun: ...
    def list(self, page: int, page_size: int) -> tuple[list[InsightRun], int]: ...


class SqlAlchemyInsightRepository(InsightRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self, request: InsightRequest, source_count: int, insights: list[dict[str, Any]]
    ) -> InsightRun:
        run = InsightRun(
            engine_version="1.0",
            request_payload=request.model_dump(mode="json"),
            source_record_count=source_count,
            insight_count=len(insights),
        )
        self.db.add(run)
        self.db.flush()
        self.db.add_all([Insight(run_id=run.id, **item) for item in insights])
        self.db.commit()
        return self.get(run.id)

    def get(self, run_id: int) -> InsightRun:
        run = self.db.scalar(
            select(InsightRun)
            .options(selectinload(InsightRun.insights))
            .where(InsightRun.id == run_id)
        )
        if run is None:
            raise InsightRunNotFoundError(f"Insight run {run_id} not found")
        return run

    def list(self, page: int, page_size: int) -> tuple[list[InsightRun], int]:
        total = self.db.scalar(select(func.count(InsightRun.id))) or 0
        rows = self.db.scalars(
            select(InsightRun)
            .order_by(InsightRun.calculated_at.desc(), InsightRun.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(rows), total
