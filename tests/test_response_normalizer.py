import pytest

from backend.app.providers.base import GenerateResponse
from backend.app.providers.pricing import UsageCost
from research.normalizer import (
    ResponseErrorType,
    ResponseNormalizationError,
    classify_error,
    normalize,
)


def test_normalizer_produces_unified_response() -> None:
    normalized = normalize(
        GenerateResponse(
            provider="perplexity",
            model="sonar-pro",
            content="Answer",
            citations=[{"url": "https://example.org"}],
            finish_reason="stop",
            usage=UsageCost(
                prompt_tokens=10,
                completion_tokens=4,
                total_tokens=14,
                estimated_cost=0.001,
                currency="USD",
                provider="perplexity",
                model="sonar-pro",
            ),
            metadata={"request_id": "abc"},
        )
    )
    assert normalized.content == "Answer"
    assert normalized.citations == [{"url": "https://example.org"}]
    assert normalized.finish_reason == "stop"
    assert normalized.usage.input_tokens == 10
    assert normalized.usage.output_tokens == 4
    assert normalized.usage.total_tokens == 14
    assert normalized.usage.cost == 0.001
    assert normalized.metadata["provider"] == "perplexity"


def test_normalizer_rejects_invalid_provider_response() -> None:
    with pytest.raises(ResponseNormalizationError) as caught:
        normalize({"provider": "openai", "content": 42})
    assert caught.value.error_type == ResponseErrorType.VALIDATION_ERROR


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("request timed out", ResponseErrorType.TIMEOUT),
        ("provider unavailable", ResponseErrorType.PROVIDER_ERROR),
        ("response validation failed", ResponseErrorType.VALIDATION_ERROR),
        ("invalid JSON parsing", ResponseErrorType.PARSING_ERROR),
    ],
)
def test_error_classification(message: str, expected: ResponseErrorType) -> None:
    assert classify_error(message) == expected
