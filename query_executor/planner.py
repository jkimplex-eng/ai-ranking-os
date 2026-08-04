from query_executor.schemas import ExecutionMode, ExecutionPlan


class InvalidExecutionPlanError(ValueError):
    """Execution Plan is internally inconsistent."""


def validate_plan(plan: ExecutionPlan) -> ExecutionPlan:
    step_ids = [step.step_id for step in plan.steps]
    if len(step_ids) != len(set(step_ids)):
        raise InvalidExecutionPlanError("Execution Plan step_id values must be unique")
    if plan.mode == ExecutionMode.SINGLE and len(plan.steps) != 1:
        raise InvalidExecutionPlanError("SINGLE plans must contain exactly one step")
    return plan

