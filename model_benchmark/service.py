from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy.orm import Session

from backend.app.llm_router.ports import LLMRouterPort
from backend.app.llm_router.schemas import RouteRequest
from backend.app.llm_router.service import router_service
from model_benchmark.models import ModelBenchmarkResult, ModelBenchmarkRun
from model_benchmark.repository import ModelBenchmarkRepository
from model_benchmark.schemas import (
    ModelBenchmarkRead,
    ModelBenchmarkRequest,
    ModelBenchmarkResultRead,
)


class ModelBenchmarkService:
    def __init__(self, db: Session, router: LLMRouterPort = router_service) -> None:
        self.db = db
        self.router = router
        self.repository = ModelBenchmarkRepository(db)

    def run(self, payload: ModelBenchmarkRequest) -> ModelBenchmarkRead:
        now = datetime.now(UTC)
        run = ModelBenchmarkRun(
            prompt=payload.prompt, iterations=payload.iterations, created_at=now
        )
        self.db.add(run)
        self.db.flush()
        for selection in payload.models:
            responses = []
            latencies = []
            costs = []
            for _ in range(payload.iterations):
                started = perf_counter()
                response = self.router.generate(
                    self.db,
                    RouteRequest(
                        query=payload.prompt,
                        allowed_models=[selection.model],
                    ),
                )
                latencies.append((perf_counter() - started) * 1000)
                responses.append(str(response.get("content", "")))
                usage = response.get("usage", {})
                costs.append(float(usage.get("estimated_cost", usage.get("cost", 0))))
            stability = 1.0 - (len(set(responses)) - 1) / len(responses)
            coverage = len(
                set(payload.prompt.casefold().split()) & set(responses[0].casefold().split())
            )
            quality = min(100.0, 50.0 + coverage * 5 + min(len(responses[0]), 500) / 20)
            self.db.add(
                ModelBenchmarkResult(
                    run_id=run.id,
                    provider=selection.provider,
                    model=selection.model,
                    latency_ms=round(sum(latencies) / len(latencies), 3),
                    cost_usd=round(sum(costs) / len(costs), 8),
                    quality_score=round(quality, 3),
                    response_length=len(responses[0]),
                    stability_score=round(stability, 3),
                    created_at=now,
                )
            )
        self.db.commit()
        return self.get(run.id)

    def get(self, run_id: int) -> ModelBenchmarkRead:
        run, results = self.repository.get(run_id)
        return ModelBenchmarkRead(
            id=run.id,
            prompt=run.prompt,
            iterations=run.iterations,
            created_at=run.created_at,
            results=[ModelBenchmarkResultRead.model_validate(item) for item in results],
        )
