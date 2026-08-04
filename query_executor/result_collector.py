import json
from collections import Counter
from typing import Any

from query_executor.schemas import StepResult, StepState


def collect_single(results: list[StepResult]) -> Any:
    return results[0].output if results and results[0].state == StepState.COMPLETED else None


def collect_parallel(results: list[StepResult]) -> list[Any]:
    return [result.output for result in results if result.state == StepState.COMPLETED]


def collect_ensemble(results: list[StepResult]) -> dict[str, Any]:
    completed = [result.output for result in results if result.state == StepState.COMPLETED]
    if not completed:
        return {"consensus": None, "provider_outputs": []}
    serialized = [json.dumps(item, sort_keys=True, default=str) for item in completed]
    consensus_json, votes = Counter(serialized).most_common(1)[0]
    return {
        "consensus": json.loads(consensus_json),
        "votes": votes,
        "provider_outputs": completed,
    }


def collect_fallback(results: list[StepResult]) -> Any:
    completed = next(
        (result.output for result in results if result.state == StepState.COMPLETED),
        None,
    )
    return completed

