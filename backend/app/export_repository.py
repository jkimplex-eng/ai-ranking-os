from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.models import AnalyticsRun
from export_engine.repository import ExportRepository, ExportRow, ExportSourceNotFoundError


class PlatformExportRepository(ExportRepository):
    """Infrastructure adapter that flattens persisted public analytics results."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def rows(self, analytics_run_ids: list[int]) -> Iterable[ExportRow]:
        runs = self.db.scalars(
            select(AnalyticsRun)
            .where(AnalyticsRun.id.in_(analytics_run_ids))
            .order_by(AnalyticsRun.id)
        ).all()
        found = {run.id for run in runs}
        missing = set(analytics_run_ids) - found
        if missing:
            raise ExportSourceNotFoundError(
                f"Analytics runs not found: {', '.join(map(str, sorted(missing)))}"
            )
        for run in runs:
            for group_index, group in enumerate(run.result_payload.get("groups", []), start=1):
                row: ExportRow = {
                    "run_id": run.id,
                    "engine_version": run.engine_version,
                    "calculated_at": run.calculated_at.isoformat(),
                    "group_index": group_index,
                    "interval_start": group.get("interval_start"),
                    "record_count": group.get("record_count", 0),
                }
                row.update(
                    {
                        f"dimension.{key}": value
                        for key, value in group.get("dimensions", {}).items()
                    }
                )
                for metric, statistics in group.get("metrics", {}).items():
                    for statistic, value in statistics.get("values", {}).items():
                        row[f"metric.{metric}.{statistic.casefold()}"] = value
                yield row
