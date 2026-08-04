from backend.app.llm_router.schemas import ModelRead, RouteRequest
from query_executor.schemas import ExecutionMode, ExecutionPlan


def build_execution_plan(
    request: RouteRequest,
    *,
    correlation_id: str,
    models: list[ModelRead],
    mode: ExecutionMode,
) -> ExecutionPlan:
    return ExecutionPlan(
        plan_id=f"router-{correlation_id}",
        request_id=correlation_id,
        mode=mode,
        steps=[
            {
                "step_id": f"model-{index}",
                "provider": model.provider,
                "payload": {
                    "model": model.id,
                    "query": request.query,
                    "max_tokens": request.max_output_tokens,
                    "metadata": {
                        **request.metadata,
                        "correlation_id": correlation_id,
                    },
                },
                "timeout_seconds": 30,
                "max_retries": 2,
                "required": index == 1,
            }
            for index, model in enumerate(models, start=1)
        ],
        metadata={
            "correlation_id": correlation_id,
            "source": "production_llm_router",
        },
    )

