from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.llm_router.adapters import RuntimeProviderReadiness, SqlAlchemyModelEvaluation
from backend.app.llm_router.cost_optimizer import settle_reservation
from backend.app.llm_router.models import RouterCostLog
from backend.app.llm_router.pipeline import route
from backend.app.llm_router.schemas import RouteRequest
from query_executor.dispatcher import Dispatcher
from query_executor.executor import execute_plan


class RouterExecutionError(RuntimeError):
    pass


class LLMRouterService:
    """The platform's only public route-and-execute entry point for LLM work."""

    def __init__(self, dispatcher: Dispatcher | None = None) -> None:
        self.dispatcher = dispatcher or Dispatcher()

    def generate(self, db: Session, request: RouteRequest) -> dict[str, Any]:
        decision = self.decide(db, request)
        result = execute_plan(
            str(uuid4()),
            decision.plan,
            self.dispatcher,
        )
        success = str(result.state) == "COMPLETED"
        settle_reservation(db, decision.correlation_id, success=success)
        if not success:
            raise RouterExecutionError(result.error or "Routed LLM execution failed")
        output = result.output
        if not isinstance(output, dict):
            output = {"content": str(output)}
        output.setdefault("routing", decision.model_dump(mode="json"))
        usage = output.get("usage", {}) if isinstance(output.get("usage"), dict) else {}
        db.add(
            RouterCostLog(
                correlation_id=decision.correlation_id,
                model_id=str(output.get("model", decision.selected_models[0])),
                provider=str(output.get("provider", decision.scores[0].provider)),
                input_tokens=int(usage.get("prompt_tokens", usage.get("input_tokens", 0))),
                output_tokens=int(
                    usage.get("completion_tokens", usage.get("output_tokens", 0))
                ),
                cost_usd=float(usage.get("estimated_cost", usage.get("cost", 0))),
                cost_type="ACTUAL",
                created_at=datetime.now(UTC),
            )
        )
        db.commit()
        return output

    @staticmethod
    def decide(db: Session, request: RouteRequest):
        return route(
            db,
            request,
            readiness=RuntimeProviderReadiness(db),
            evaluation=SqlAlchemyModelEvaluation(db),
        )


router_service = LLMRouterService()
