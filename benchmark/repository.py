from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from benchmark.models import BenchmarkEntry, BenchmarkRun
from benchmark.schemas import BenchmarkRequest


class BenchmarkNotFoundError(LookupError):
    pass


class BenchmarkRepository(Protocol):
    def create(self, request: BenchmarkRequest, entries: list[dict[str, Any]]) -> BenchmarkRun: ...
    def get(self, run_id: int) -> BenchmarkRun: ...
    def list(self, page: int, page_size: int) -> tuple[list[BenchmarkRun], int]: ...


class SqlAlchemyBenchmarkRepository(BenchmarkRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, request: BenchmarkRequest, entries: list[dict[str, Any]]) -> BenchmarkRun:
        run = BenchmarkRun(
            engine_version="1.0",
            metrics=request.metrics,
            entity_count=len(entries),
            date_from=request.date_from,
            date_to=request.date_to,
        )
        self.db.add(run)
        self.db.flush()
        for entry in entries:
            self.db.add(BenchmarkEntry(run_id=run.id, **entry))
        self.db.commit()
        return self.get(run.id)

    def get(self, run_id: int) -> BenchmarkRun:
        run = self.db.scalar(
            select(BenchmarkRun)
            .options(selectinload(BenchmarkRun.entries))
            .where(BenchmarkRun.id == run_id)
        )
        if run is None:
            raise BenchmarkNotFoundError(f"Benchmark {run_id} not found")
        return run

    def list(self, page: int, page_size: int) -> tuple[list[BenchmarkRun], int]:
        total = self.db.scalar(select(func.count(BenchmarkRun.id))) or 0
        rows = self.db.scalars(
            select(BenchmarkRun)
            .order_by(BenchmarkRun.calculated_at.desc(), BenchmarkRun.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(rows), total
