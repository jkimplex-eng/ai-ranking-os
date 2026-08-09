from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.providers.models import ProviderUsageRecord
from cost_analytics.schemas import CostAnalyticsRead, CostBreakdown


class CostAnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def report(self) -> CostAnalyticsRead:
        records = list(self.db.scalars(select(ProviderUsageRecord)))
        groups: dict[str, dict[str, list[float]]] = {
            "research": defaultdict(lambda: [0.0, 0.0]),
            "model": defaultdict(lambda: [0.0, 0.0]),
            "user": defaultdict(lambda: [0.0, 0.0]),
        }
        free_tokens = paid_tokens = 0
        for record in records:
            tokens = record.total_tokens
            if record.estimated_cost == 0:
                free_tokens += tokens
            else:
                paid_tokens += tokens
            keys = {
                "research": str(record.research_id or record.execution_id),
                "model": f"{record.provider}/{record.model}",
                "user": str(record.user_id or "anonymous"),
            }
            for group, key in keys.items():
                groups[group][key][0] += record.estimated_cost
                groups[group][key][1] += tokens

        def breakdown(group: str) -> list[CostBreakdown]:
            return [
                CostBreakdown(key=key, cost_usd=round(values[0], 8), tokens=int(values[1]))
                for key, values in sorted(groups[group].items(), key=lambda item: -item[1][0])
            ]

        return CostAnalyticsRead(
            total_cost_usd=round(sum(item.estimated_cost for item in records), 8),
            total_tokens=sum(item.total_tokens for item in records),
            free_tokens=free_tokens,
            paid_tokens=paid_tokens,
            by_research=breakdown("research"),
            by_model=breakdown("model"),
            by_user=breakdown("user"),
        )
