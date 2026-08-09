from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.llm_router.config_loader import policy_config, provider_config, router_config
from backend.app.llm_router.models import (
    CircuitBreakerRecord,
    ModelVersionRecord,
    RegisteredModel,
    RoutingPolicy,
)
from backend.app.llm_router.schemas import (
    CircuitState,
    ModelCreate,
    ModelRead,
    ModelUpdate,
    PolicyRead,
    PolicyUpdate,
    Pricing,
)


class RegistryError(Exception):
    """Base registry error."""


class RegistryNotFoundError(RegistryError):
    """Registry entity does not exist."""


class RegistryConflictError(RegistryError):
    """Registry entity conflicts with current state."""


def _now() -> datetime:
    return datetime.now(UTC)


def model_to_read(
    model: RegisteredModel,
    circuit_state: str = CircuitState.CLOSED,
) -> ModelRead:
    return ModelRead(
        id=model.id,
        provider=model.provider,
        display_name=model.display_name,
        version=model.version,
        release_date=model.release_date,
        status=model.status,
        tier=model.tier,
        capabilities=model.capabilities,
        pricing=Pricing(
            input_per_million=model.input_cost_per_million,
            output_per_million=model.output_cost_per_million,
        ),
        latency_ms=model.latency_ms,
        tokens_per_second=model.tokens_per_second,
        average_latency=model.average_latency,
        benchmark_score=model.benchmark_score,
        quality=model.quality,
        availability=model.availability,
        context_window=model.context_window,
        hallucination_rate=model.hallucination_rate,
        domains=model.domains,
        languages=model.languages,
        region=model.region,
        success_probability=model.success_probability,
        reasoning=model.reasoning,
        multimodal=model.multimodal,
        embeddings=model.embeddings,
        json_mode=model.json_mode,
        tool_calling=model.tool_calling,
        metadata=model.metadata_payload,
        created_at=model.created_at,
        updated_at=model.updated_at,
        circuit_state=circuit_state,
    )


def policy_to_read(policy: RoutingPolicy) -> PolicyRead:
    return PolicyRead.model_validate(policy)


class ModelRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: ModelCreate) -> ModelRead:
        now = _now()
        model = RegisteredModel(
            id=payload.id,
            provider=payload.provider.casefold(),
            display_name=payload.display_name,
            version=payload.version,
            release_date=payload.release_date,
            status=payload.status,
            tier=payload.tier,
            capabilities=payload.capabilities,
            input_cost_per_million=payload.pricing.input_per_million,
            output_cost_per_million=payload.pricing.output_per_million,
            latency_ms=payload.latency_ms,
            tokens_per_second=payload.tokens_per_second,
            average_latency=payload.average_latency or payload.latency_ms,
            benchmark_score=payload.benchmark_score,
            quality=payload.quality,
            availability=payload.availability,
            context_window=payload.context_window,
            hallucination_rate=payload.hallucination_rate,
            domains=payload.domains,
            languages=payload.languages,
            region=payload.region,
            success_probability=payload.success_probability,
            reasoning=payload.reasoning,
            multimodal=payload.multimodal,
            embeddings=payload.embeddings,
            json_mode=payload.json_mode,
            tool_calling=payload.tool_calling,
            metadata_payload=payload.metadata,
            created_at=now,
            updated_at=now,
        )
        self.db.add(model)
        self.db.flush()
        self._record_version(model, now)
        self.db.add(
            CircuitBreakerRecord(
                model_id=payload.id,
                state=CircuitState.CLOSED,
                failure_count=0,
                success_count=0,
                updated_at=now,
            )
        )
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise RegistryConflictError(f"Model {payload.id} already exists") from error
        return model_to_read(model)

    def get(self, model_id: str) -> ModelRead:
        model = self.db.get(RegisteredModel, model_id)
        if model is None:
            raise RegistryNotFoundError(f"Model {model_id} not found")
        circuit = self.db.get(CircuitBreakerRecord, model_id)
        return model_to_read(
            model,
            circuit.state if circuit else CircuitState.CLOSED,
        )

    def list(
        self,
        *,
        page: int,
        page_size: int,
        provider: str | None = None,
        status: str | None = None,
        capability: str | None = None,
        search: str | None = None,
    ) -> tuple[list[ModelRead], int]:
        filters = []
        if provider:
            filters.append(RegisteredModel.provider == provider.casefold())
        if status:
            filters.append(RegisteredModel.status == status.upper())
        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    RegisteredModel.id.ilike(pattern),
                    RegisteredModel.display_name.ilike(pattern),
                )
            )
        query = select(RegisteredModel).where(*filters).order_by(RegisteredModel.id)
        all_models = list(self.db.scalars(query))
        if capability:
            all_models = [
                model for model in all_models if capability in model.capabilities
            ]
        total = len(all_models)
        start = (page - 1) * page_size
        models = all_models[start : start + page_size]
        circuits = {
            record.model_id: record.state
            for record in self.db.scalars(
                select(CircuitBreakerRecord).where(
                    CircuitBreakerRecord.model_id.in_([model.id for model in models])
                )
            )
        } if models else {}
        return [
            model_to_read(model, circuits.get(model.id, CircuitState.CLOSED))
            for model in models
        ], total

    def all_active(self) -> list[ModelRead]:
        models, _ = self.list(page=1, page_size=1000, status="ACTIVE")
        return models

    def update(self, model_id: str, payload: ModelUpdate) -> ModelRead:
        model = self.db.get(RegisteredModel, model_id)
        if model is None:
            raise RegistryNotFoundError(f"Model {model_id} not found")
        changes = payload.model_dump(exclude_unset=True)
        pricing = changes.pop("pricing", None)
        metadata = changes.pop("metadata", None)
        for field, value in changes.items():
            setattr(model, field, value)
        if pricing is not None:
            model.input_cost_per_million = pricing["input_per_million"]
            model.output_cost_per_million = pricing["output_per_million"]
        if metadata is not None:
            model.metadata_payload = metadata
        model.updated_at = _now()
        self._record_version(model, model.updated_at)
        self.db.commit()
        return self.get(model_id)

    def versions(self, model_id: str) -> list[ModelVersionRecord]:
        if self.db.get(RegisteredModel, model_id) is None:
            raise RegistryNotFoundError(f"Model {model_id} not found")
        return list(
            self.db.scalars(
                select(ModelVersionRecord)
                .where(ModelVersionRecord.model_id == model_id)
                .order_by(ModelVersionRecord.created_at.desc(), ModelVersionRecord.id.desc())
            )
        )

    def _record_version(self, model: RegisteredModel, created_at: datetime) -> None:
        snapshot = {
            "display_name": model.display_name,
            "provider": model.provider,
            "context_length": model.context_window,
            "input_price": model.input_cost_per_million,
            "output_price": model.output_cost_per_million,
            "tokens_per_second": model.tokens_per_second,
            "average_latency": model.average_latency,
            "benchmark_score": model.benchmark_score,
            "capabilities": model.capabilities,
        }
        self.db.add(
            ModelVersionRecord(
                model_id=model.id,
                version=model.version,
                snapshot=snapshot,
                created_at=created_at,
            )
        )

    def delete(self, model_id: str) -> None:
        model = self.db.get(RegisteredModel, model_id)
        if model is None:
            raise RegistryNotFoundError(f"Model {model_id} not found")
        circuit = self.db.get(CircuitBreakerRecord, model_id)
        if circuit:
            self.db.delete(circuit)
        self.db.delete(model)
        self.db.commit()


class PolicyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, policy_id: str) -> PolicyRead:
        policy = self.db.get(RoutingPolicy, policy_id)
        if policy is None:
            raise RegistryNotFoundError(f"Policy {policy_id} not found")
        return policy_to_read(policy)

    def list(self) -> list[PolicyRead]:
        return [
            policy_to_read(policy)
            for policy in self.db.scalars(select(RoutingPolicy).order_by(RoutingPolicy.id))
        ]

    def update(self, policy_id: str, payload: PolicyUpdate) -> PolicyRead:
        policy = self.db.get(RoutingPolicy, policy_id)
        if policy is None:
            raise RegistryNotFoundError(f"Policy {policy_id} not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(policy, field, value)
        policy.updated_at = _now()
        self.db.commit()
        return policy_to_read(policy)


def ensure_seeded(db: Session) -> None:
    if not db.scalar(select(func.count()).select_from(RegisteredModel)):
        repository = ModelRepository(db)
        for raw in provider_config().get("models", []):
            repository.create(
                ModelCreate(
                    id=raw["id"],
                    provider=raw["provider"],
                    display_name=raw["display_name"],
                    status=raw["status"],
                    tier=raw["tier"],
                    capabilities=raw["capabilities"],
                    pricing=raw["pricing"],
                    latency_ms=raw["latency_ms"],
                    quality=raw["quality"],
                    availability=raw["availability"],
                    context_window=raw["context_window"],
                    hallucination_rate=raw["hallucination_rate"],
                    domains=raw["domains"],
                    languages=raw["languages"],
                    region=raw.get("region", "GLOBAL"),
                    success_probability=raw.get("success_probability", 0.95),
                )
            )
    if not db.scalar(select(func.count()).select_from(RoutingPolicy)):
        budgets = router_config().get("budgets", {})
        now = _now()
        for raw in policy_config().get("policies", []):
            db.add(
                RoutingPolicy(
                    id=raw["id"],
                    name=raw["name"],
                    enabled=True,
                    execution_mode=raw["execution_mode"],
                    top_k=raw["top_k"],
                    weights=raw["weights"],
                    required_capabilities=raw.get("required_capabilities", []),
                    daily_budget_usd=budgets.get("daily_usd"),
                    monthly_budget_usd=budgets.get("monthly_usd"),
                    settings={},
                    updated_at=now,
                )
            )
        db.commit()
