from sqlalchemy.orm import Session

from backend.app.llm_router.config_loader import router_config
from backend.app.llm_router.registry import PolicyRepository
from backend.app.llm_router.schemas import PolicyRead, RouteRequest, RouterStrategy, RoutingProfile

PROFILE_POLICIES = {
    RoutingProfile.FAST: ("latency-critical", RouterStrategy.FASTEST),
    RoutingProfile.BALANCED: ("balanced", RouterStrategy.BALANCED),
    RoutingProfile.HIGH_QUALITY: ("quality-first", RouterStrategy.HIGHEST_QUALITY),
    RoutingProfile.FREE: ("cost-optimized", RouterStrategy.FREE_ONLY),
    RoutingProfile.PRIVATE: ("latency-critical", RouterStrategy.LOCAL_ONLY),
    RoutingProfile.ENTERPRISE: ("research-grade", RouterStrategy.HIGHEST_QUALITY),
}


def profile_policy(profile: RoutingProfile) -> tuple[str, RouterStrategy]:
    return PROFILE_POLICIES[profile]

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
    profile_id, _ = profile_policy(request.profile)
    default_id = router_config().get("defaults", {}).get("policy_id", profile_id)
    repository = PolicyRepository(db)
    policy = (
        repository.get(request.policy_id)
        if request.policy_id
        else repository.get(TASK_POLICIES[request.task_type.casefold()])
        if request.task_type and request.task_type.casefold() in TASK_POLICIES
        else repository.get(profile_id)
    ) or repository.get(default_id)
    if not policy.enabled:
        raise ValueError(f"Routing policy {policy.id} is disabled")
    return policy

