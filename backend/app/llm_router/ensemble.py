from backend.app.llm_router.execution_plan import build_execution_plan
from backend.app.llm_router.schemas import ModelRead, RouteRequest
from query_executor.schemas import ExecutionMode, ExecutionPlan


def build_ensemble_plan(
    request: RouteRequest,
    correlation_id: str,
    models: list[ModelRead],
) -> ExecutionPlan:
    return build_execution_plan(
        request,
        correlation_id=correlation_id,
        models=models,
        mode=ExecutionMode.ENSEMBLE,
    )
