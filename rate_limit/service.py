from rate_limit.models import RateLimitPolicy
from rate_limit.schemas import PolicyRead


class RateLimitError(ValueError):
    pass


class RateLimitService:
    def __init__(self, repository, backend):
        self.repository = repository
        self.backend = backend

    def create(self, data):
        return PolicyRead.model_validate(self.repository.save(RateLimitPolicy(**data.model_dump())))

    def list(self):
        return [PolicyRead.model_validate(x) for x in self.repository.list()]

    def check(self, policy_id, subject):
        policy = self.repository.get(policy_id)
        if not policy or not policy.enabled:
            raise RateLimitError("Policy not found or disabled")
        method = getattr(self.backend, policy.algorithm)
        return method(f"{policy.id}:{subject}", policy.limit, policy.window_seconds, policy.burst)
