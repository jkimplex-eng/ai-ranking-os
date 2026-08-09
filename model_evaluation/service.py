from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.providers.base import GenerateRequest
from backend.app.providers.factory import ProviderFactory, factory
from model_evaluation.models import ModelEvaluationScore
from model_evaluation.schemas import (
    CapabilityMatrixRead,
    EvaluationRequest,
    EvaluationScoreRead,
)

EVALUATIONS = {
    "entity_extraction": ("Extract entities as JSON: Acme makes Widget.", ("acme", "widget")),
    "intent": ("Classify intent: compare Acme and Beta.", ("compare",)),
    "summarization": ("Summarize: AI visibility measures brand presence.", ("visibility",)),
    "knowledge_graph": ("Create graph relation: Acme produces Widget.", ("acme", "widget")),
    "recommendation": ("Recommend how to improve weak citations.", ("citation",)),
    "report": ("Write an executive AI visibility report.", ("visibility",)),
}


def empirical_model_scores(db: Session, task: str | None) -> dict[str, float]:
    if not task or task not in EVALUATIONS:
        return {}
    rows = db.execute(
        select(
            ModelEvaluationScore.provider,
            ModelEvaluationScore.model,
            func.avg(ModelEvaluationScore.score),
        )
        .where(ModelEvaluationScore.task == task)
        .group_by(ModelEvaluationScore.provider, ModelEvaluationScore.model)
    )
    return {f"{provider}/{model}": float(score) / 100 for provider, model, score in rows}


class ModelEvaluationService:
    def __init__(self, db: Session, provider_factory: ProviderFactory = factory) -> None:
        self.db = db
        self.providers = provider_factory

    def evaluate(self, payload: EvaluationRequest) -> list[EvaluationScoreRead]:
        tasks = payload.tasks or list(EVALUATIONS)
        unknown = set(tasks) - EVALUATIONS.keys()
        if unknown:
            raise ValueError(f"Unknown evaluation tasks: {', '.join(sorted(unknown))}")
        results = []
        now = datetime.now(UTC)
        for selected in payload.models:
            provider = self.providers.create(selected.provider)
            for task in tasks:
                prompt, keywords = EVALUATIONS[task]
                started = perf_counter()
                response = provider.generate(GenerateRequest(model=selected.model, prompt=prompt))
                latency = (perf_counter() - started) * 1000
                content = response.content.casefold()
                score = round(100 * sum(word in content for word in keywords) / len(keywords), 3)
                record = ModelEvaluationScore(
                    provider=selected.provider,
                    model=selected.model,
                    task=task,
                    score=score,
                    latency_ms=round(latency, 3),
                    version="1.0",
                    created_at=now,
                )
                self.db.add(record)
                results.append(EvaluationScoreRead.model_validate(record, from_attributes=True))
        self.db.commit()
        return results

    def matrix(self) -> CapabilityMatrixRead:
        rows = self.db.execute(
            select(
                ModelEvaluationScore.provider,
                ModelEvaluationScore.model,
                ModelEvaluationScore.task,
                func.avg(ModelEvaluationScore.score),
            ).group_by(
                ModelEvaluationScore.provider,
                ModelEvaluationScore.model,
                ModelEvaluationScore.task,
            )
        )
        matrix: dict[str, dict[str, float]] = {}
        for provider, model, task, score in rows:
            matrix.setdefault(f"{provider}/{model}", {})[task] = round(float(score), 3)
        return CapabilityMatrixRead(models=matrix, tasks=list(EVALUATIONS))
