import json
from collections.abc import Iterator

from query_executor.schemas import ExecutorResult


def stream_result(result: ExecutorResult) -> Iterator[str]:
    yield json.dumps(
        {"event": "execution_started", "execution_id": result.execution_id}
    ) + "\n"
    for step in result.results:
        yield json.dumps(
            {
                "event": "step_result",
                "execution_id": result.execution_id,
                "data": step.model_dump(mode="json"),
            }
        ) + "\n"
    yield json.dumps(
        {
            "event": "execution_finished",
            "execution_id": result.execution_id,
            "data": result.model_dump(mode="json"),
        }
    ) + "\n"

