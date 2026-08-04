from typing import Any

from fastapi import FastAPI

from ai_visibility.schemas import VisibilityResult
from entity_extraction.schemas import ExtractionResult
from query_executor.schemas import ExecutionPlan, ExecutorResult
from query_intent.schemas import IntentResult
from validation.schema_validator import schema_signature, validate_model

REQUIRED_API_OPERATIONS = {
    ("POST", "/router/route"),
    ("POST", "/intent/classify"),
    ("POST", "/executor/run"),
    ("POST", "/executor/stream"),
    ("POST", "/entity-extraction/extract"),
    ("POST", "/visibility/calculate"),
    ("GET", "/system/health"),
    ("GET", "/metrics"),
    ("POST", "/research"),
    ("POST", "/research/{research_id}/run"),
    ("POST", "/research-tasks"),
    ("POST", "/responses"),
}


def validate_api_contract(app: FastAPI) -> tuple[bool, dict[str, Any]]:
    specification = app.openapi()
    actual = {
        (method.upper(), path)
        for path, operations in specification["paths"].items()
        for method in operations
    }
    missing = sorted(REQUIRED_API_OPERATIONS - actual)
    return not missing, {
        "required_operations": len(REQUIRED_API_OPERATIONS),
        "missing": [{"method": method, "path": path} for method, path in missing],
    }


def validate_stage_schemas(stages: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    validations = {
        "intent": validate_model(IntentResult, stages["intent"]),
        "router": validate_model(ExecutionPlan, stages["router"]),
        "executor": validate_model(ExecutorResult, stages["executor"]),
        "entity_extraction": validate_model(
            ExtractionResult,
            stages["entity_extraction"],
        ),
        "visibility": validate_model(VisibilityResult, stages["visibility"]),
    }
    errors = {stage: error for stage, (valid, error) in validations.items() if not valid}
    return not errors, {
        "errors": errors,
        "signatures": {
            "intent": schema_signature(IntentResult),
            "router": schema_signature(ExecutionPlan),
            "executor": schema_signature(ExecutorResult),
            "entity_extraction": schema_signature(ExtractionResult),
            "visibility": schema_signature(VisibilityResult),
        },
    }
