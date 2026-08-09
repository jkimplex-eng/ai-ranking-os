from sqlalchemy.orm import Session

from backend.app.llm_router.config_loader import router_config
from backend.app.llm_router.registry import PolicyRepository
from backend.app.llm_router.schemas import PolicyRead, RouteRequest, RouterStrategy

TASK_STRATEGIES = {
    "entity_extraction": RouterStrategy.LOCAL_ONLY,
    "final_report": RouterStrategy.HIGHEST_QUALITY,
    "embeddings": RouterStrategy.CHEAPEST,
    "classification": RouterStrategy.FREE_ONLY,
}
TASK_POLICIES = {
    "entity_extraction": "latency-critical",
    "final_report": "quality-first",
    "embeddings": "cost-optimized",
    "classification": "cost-optimized",
}


def strategy_for_task(task_type: str | None) -> RouterStrategy | None:
    return TASK_STRATEGIES.get(task_type.casefold()) if task_type else None


def resolve_policy(db: Session, request: RouteRequest) -> PolicyRead:
    default_id = router_config().get("defaults", {}).get("policy_id", "quality-first")
    repository = PolicyRepository(db)
    policy = (
        repository.get(request.policy_id)
        if request.policy_id
        else repository.get(TASK_POLICIES[request.task_type.casefold()])
        if request.task_type and request.task_type.casefold() in TASK_POLICIES
        else None
    ) or repository.get(default_id)
    if not policy.enabled:
        raise ValueError(f"Routing policy {policy.id} is disabled")
    return policy

