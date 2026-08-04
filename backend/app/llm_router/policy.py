from sqlalchemy.orm import Session

from backend.app.llm_router.config_loader import router_config
from backend.app.llm_router.registry import PolicyRepository
from backend.app.llm_router.schemas import PolicyRead, RouteRequest


def resolve_policy(db: Session, request: RouteRequest) -> PolicyRead:
    default_id = router_config().get("defaults", {}).get("policy_id", "quality-first")
    policy = PolicyRepository(db).get(request.policy_id or default_id)
    if not policy.enabled:
        raise ValueError(f"Routing policy {policy.id} is disabled")
    return policy

