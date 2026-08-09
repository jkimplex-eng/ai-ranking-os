from sqlalchemy import select
from sqlalchemy.orm import Session

from model_benchmark.models import ModelBenchmarkResult, ModelBenchmarkRun


class ModelBenchmarkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, run_id: int) -> tuple[ModelBenchmarkRun, list[ModelBenchmarkResult]]:
        run = self.db.get(ModelBenchmarkRun, run_id)
        if run is None:
            raise LookupError(f"Model benchmark {run_id} not found")
        results = list(
            self.db.scalars(
                select(ModelBenchmarkResult)
                .where(ModelBenchmarkResult.run_id == run_id)
                .order_by(ModelBenchmarkResult.quality_score.desc())
            )
        )
        return run, results
