from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from provider_recommendation.ports import ProviderUsageFact
from provider_recommendation.service import SmartProviderRecommendationService


class FakeUsage:
    def usage(self, research_id: int) -> list[ProviderUsageFact]:
        return [
            ProviderUsageFact("openai", "gpt", 1000, 0.02, 100),
            ProviderUsageFact("gemini", "flash", 500, 0.01, 100),
        ]


def test_smart_provider_recommendations_are_deterministic() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        service = SmartProviderRecommendationService(db, FakeUsage())
        results = service.generate(42)
        assert [item.recommendation_type for item in results] == ["COST", "LATENCY", "QUALITY"]
        assert results[0].recommended_provider == "ollama"
        assert results[0].expected_savings_usd == 0.03
        assert results[1].recommended_provider == "gemini"
        assert results[1].expected_speedup_percent == 50
    Base.metadata.drop_all(engine)
