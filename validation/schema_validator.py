import json
from typing import Any

from pydantic import BaseModel, ValidationError


def validate_model(model: type[BaseModel], payload: Any) -> tuple[bool, str | None]:
    try:
        model.model_validate(payload)
    except ValidationError as error:
        return False, str(error)
    return True, None


def validate_json_serializable(payload: Any) -> tuple[bool, str | None]:
    try:
        json.dumps(payload, default=str)
    except (TypeError, ValueError) as error:
        return False, str(error)
    return True, None


def schema_signature(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    return {
        "title": schema.get("title", model.__name__),
        "required": sorted(schema.get("required", [])),
        "properties": sorted(schema.get("properties", {})),
    }

