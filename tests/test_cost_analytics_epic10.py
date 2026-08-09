from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from backend.app.providers.models import ProviderUsageRecord
from cost_analytics.service import CostAnalyticsService


def test_cost_analytics_groups_usage() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for provider, model, cost, research, user in [
            ("ollama", "llama", 0, 1, "u1"),
            ("openai", "gpt", 0.01, 1, "u1"),
        ]:
            db.add(
                ProviderUsageRecord(
                    execution_id=f"e-{provider}",
                    research_id=research,
                    user_id=user,
                    provider=provider,
                    model=model,
                    prompt_tokens=10,
                    completion_tokens=10,
                    total_tokens=20,
                    estimated_cost=cost,
                    currency="USD",
                    created_at=datetime.now(UTC),
                )
            )
        db.commit()
        report = CostAnalyticsService(db).report()
        assert report.total_cost_usd == 0.01
        assert report.free_tokens == 20
        assert report.paid_tokens == 20
        assert report.by_research[0].key == "1"
        assert len(report.by_model) == 2
    Base.metadata.drop_all(engine)
