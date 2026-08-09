from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.llm_router.models import BudgetReservation, RouterCostLog, RoutingPolicy
from backend.app.llm_router.schemas import ModelRead, PolicyRead, ScoreBreakdown


class BudgetExceededError(ValueError):
    """No execution plan can be reserved within the configured hard budget."""


def _spent(db: Session, start: datetime) -> float:
    actual = db.scalar(
        select(func.coalesce(func.sum(RouterCostLog.cost_usd), 0.0)).where(
            RouterCostLog.created_at >= start,
            RouterCostLog.cost_type == "ACTUAL",
        )
    )
    reserved = db.scalar(
        select(func.coalesce(func.sum(BudgetReservation.amount_usd), 0.0)).where(
            BudgetReservation.created_at >= start,
            BudgetReservation.state == "RESERVED",
            BudgetReservation.expires_at > datetime.now(UTC),
        )
    )
    return float(actual or 0) + float(reserved or 0)


def current_costs(db: Session) -> tuple[float, float]:
    now = datetime.now(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return _spent(db, day_start), _spent(db, day_start.replace(day=1))


def _plan_cost(scores: list[ScoreBreakdown], top_k: int) -> float:
    return sum(score.estimated_cost_usd for score in scores[:top_k])


def optimize_for_budget(
    db: Session,
    models: list[ModelRead],
    scores: list[ScoreBreakdown],
    policy: PolicyRead,
    *,
    correlation_id: str,
) -> tuple[list[ModelRead], list[ScoreBreakdown], bool]:
    # The policy row is the serialization point for all reservations under a policy.
    db.scalar(
        select(RoutingPolicy).where(RoutingPolicy.id == policy.id).with_for_update()
    )
    daily, monthly = current_costs(db)
    predicted = _plan_cost(scores, policy.top_k)

    def allowed(amount: float) -> bool:
        return (
            (policy.daily_budget_usd is None or daily + amount <= policy.daily_budget_usd)
            and (policy.monthly_budget_usd is None or monthly + amount <= policy.monthly_budget_usd)
            and (policy.per_research_budget_usd is None or amount <= policy.per_research_budget_usd)
        )

    downgraded = False
    if not allowed(predicted):
        paired = sorted(
            zip(models, scores, strict=True),
            key=lambda pair: (pair[1].estimated_cost_usd, -pair[1].total),
        )
        models = [pair[0] for pair in paired]
        scores = [pair[1] for pair in paired]
        predicted = _plan_cost(scores, policy.top_k)
        downgraded = True
    if not allowed(predicted):
        raise BudgetExceededError(f"Hard budget exceeded for policy {policy.id}")
    now = datetime.now(UTC)
    db.add(
        BudgetReservation(
            id=str(uuid4()),
            correlation_id=correlation_id,
            policy_id=policy.id,
            amount_usd=predicted,
            state="RESERVED",
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
    )
    db.flush()
    return models, scores, downgraded


def settle_reservation(db: Session, correlation_id: str, *, success: bool) -> None:
    reservation = db.scalar(
        select(BudgetReservation)
        .where(BudgetReservation.correlation_id == correlation_id)
        .with_for_update()
    )
    if reservation is None or reservation.state != "RESERVED":
        return
    reservation.state = "SETTLED" if success else "RELEASED"
    reservation.settled_at = datetime.now(UTC)
    db.commit()
