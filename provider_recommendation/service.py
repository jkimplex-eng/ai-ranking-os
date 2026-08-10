from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from provider_recommendation.models import ProviderRecommendation
from provider_recommendation.ports import ResearchUsageSource
from provider_recommendation.schemas import ProviderRecommendationRead


class SmartProviderRecommendationService:
    def __init__(self, db: Session, source: ResearchUsageSource) -> None:
        self.db = db
        self.source = source

    def generate(self, research_id: int) -> list[ProviderRecommendationRead]:
        usage = self.source.usage(research_id)
        if not usage:
            return []
        self.db.execute(
            delete(ProviderRecommendation).where(ProviderRecommendation.research_id == research_id)
        )
        total_cost = sum(item.cost for item in usage)
        fastest = min(usage, key=lambda item: item.latency_ms or float("inf"))
        slowest = max(usage, key=lambda item: item.latency_ms)
        speedup = (
            max(0.0, (slowest.latency_ms - fastest.latency_ms) / slowest.latency_ms * 100)
            if slowest.latency_ms
            else 0.0
        )
        now = datetime.now(UTC)
        records = [
            ProviderRecommendation(
                research_id=research_id,
                recommendation_type="COST",
                message=(
                    "Используйте Ollama для повторяемых задач "
                    f"и экономьте до ${total_cost:.4f}."
                ),
                recommended_provider="ollama",
                expected_savings_usd=total_cost,
                expected_speedup_percent=0,
                version="1.0",
                created_at=now,
            ),
            ProviderRecommendation(
                research_id=research_id,
                recommendation_type="LATENCY",
                message=f"{fastest.provider} быстрее в этом исследовании на {speedup:.0f}%.",
                recommended_provider=fastest.provider,
                expected_savings_usd=0,
                expected_speedup_percent=speedup,
                version="1.0",
                created_at=now,
            ),
            ProviderRecommendation(
                research_id=research_id,
                recommendation_type="QUALITY",
                message="Для финального отчёта используйте quality-first policy.",
                recommended_provider="router",
                expected_savings_usd=0,
                expected_speedup_percent=0,
                version="1.0",
                created_at=now,
            ),
        ]
        self.db.add_all(records)
        self.db.commit()
        return self.list(research_id)

    def list(self, research_id: int) -> list[ProviderRecommendationRead]:
        records = self.db.scalars(
            select(ProviderRecommendation)
            .where(ProviderRecommendation.research_id == research_id)
            .order_by(ProviderRecommendation.id)
        )
        return [ProviderRecommendationRead.model_validate(item) for item in records]
from __future__ import annotations
