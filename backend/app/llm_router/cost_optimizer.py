from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.llm_router.models import RouterCostLog
from backend.app.llm_router.schemas import ModelRead, PolicyRead, ScoreBreakdown


def current_costs(db: Session) -> tuple[float, float]:
    now = datetime.now(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start.replace(day=1)
    daily = db.scalar(
        select(func.coalesce(func.sum(RouterCostLog.cost_usd), 0.0)).where(
            RouterCostLog.created_at >= day_start
        )
    )
    monthly = db.scalar(
        select(func.coalesce(func.sum(RouterCostLog.cost_usd), 0.0)).where(
            RouterCostLog.created_at >= month_start
        )
    )
    return float(daily or 0), float(monthly or 0)


def optimize_for_budget(
    db: Session,
    models: list[ModelRead],
    scores: list[ScoreBreakdown],
    policy: PolicyRead,
) -> tuple[list[ModelRead], list[ScoreBreakdown], bool]:
    daily, monthly = current_costs(db)
    predicted = scores[0].estimated_cost_usd if scores else 0
    within_daily = policy.daily_budget_usd is None or daily + predicted <= policy.daily_budget_usd
    within_monthly = (
        policy.monthly_budget_usd is None
        or monthly + predicted <= policy.monthly_budget_usd
    )
    if within_daily and within_monthly:
        return models, scores, False
    paired = sorted(
        zip(models, scores, strict=True),
        key=lambda pair: (pair[1].estimated_cost_usd, -pair[1].total),
    )
    return [pair[0] for pair in paired], [pair[1] for pair in paired], True

