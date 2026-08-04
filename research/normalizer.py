from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from backend.app.providers.base import GenerateResponse


class ResponseErrorType(StrEnum):
    TIMEOUT = "timeout"
    PROVIDER_ERROR = "provider_error"
    VALIDATION_ERROR = "validation_error"
    PARSING_ERROR = "parsing_error"


class NormalizedUsage(BaseModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cost: float = Field(ge=0)
    currency: str = "USD"


class NormalizedResponse(BaseModel):
    content: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    finish_reason: str
    usage: NormalizedUsage
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResponseNormalizationError(ValueError):
    def __init__(self, message: str, error_type: ResponseErrorType) -> None:
        super().__init__(message)
        self.error_type = error_type


def normalize(provider_response: GenerateResponse | dict[str, Any]) -> NormalizedResponse:
    try:
        response = (
            provider_response
            if isinstance(provider_response, GenerateResponse)
            else GenerateResponse.model_validate(provider_response)
        )
    except ValidationError as error:
        raise ResponseNormalizationError(
            f"Provider response validation failed: {error}",
            ResponseErrorType.VALIDATION_ERROR,
        ) from error
    except (TypeError, ValueError, KeyError) as error:
        raise ResponseNormalizationError(
            f"Provider response parsing failed: {error}",
            ResponseErrorType.PARSING_ERROR,
        ) from error

    return NormalizedResponse(
        content=response.content,
        citations=response.citations,
        finish_reason=response.finish_reason,
        usage=NormalizedUsage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            cost=response.usage.estimated_cost,
            currency=response.usage.currency,
        ),
        metadata={
            **response.metadata,
            "provider": response.provider,
            "model": response.model,
            "cached": response.cached,
        },
    )


def normalize_error(
    error_type: ResponseErrorType,
    message: str,
) -> NormalizedResponse:
    return NormalizedResponse(
        content="",
        citations=[],
        finish_reason="error",
        usage=NormalizedUsage(
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            cost=0,
        ),
        metadata={"error_type": error_type, "error": message},
    )


def classify_error(message: str) -> ResponseErrorType:
    value = message.casefold()
    if "timeout" in value or "timed out" in value:
        return ResponseErrorType.TIMEOUT
    if "validation" in value:
        return ResponseErrorType.VALIDATION_ERROR
    if "parsing" in value or "json" in value:
        return ResponseErrorType.PARSING_ERROR
    return ResponseErrorType.PROVIDER_ERROR
