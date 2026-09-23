from types import SimpleNamespace

from product.service import FinalReportService
from research.models import ResponseProcessingStatus


def _response(response_id: int, content: str, status=ResponseProcessingStatus.PROCESSED):
    return SimpleNamespace(
        id=response_id, content=content, processing_status=status,
        provider="yandex", model="test", prompt="Какой бренд выбрать?",
        created_at=None, raw_response={}, normalized_response={},
        total_tokens=0, cost=0, latency_ms=0, finished_at=None,
        error_type=None, error_message=None,
    )


def test_report_uses_scoring_verdict_not_generic_extraction():
    research = SimpleNamespace(
        id=1, title="Brand", metadata_payload={"brand": "Brand"},
        total_tasks=3, tasks=[],
    )
    responses = [
        _response(1, "Не рекомендую Brand."),
        _response(2, "Рекомендую Brand."),
        _response(3, "", ResponseProcessingStatus.FAILED),
    ]
    base = SimpleNamespace(
        responses=responses, entities=[], citations=[],
        recommendations=[SimpleNamespace(id=1, response_id=1, content="Рекомендую Brand")],
    )
    evidence = FinalReportService._explainability(research, base, None)
    inputs = evidence["metrics"]["recommendation_score"]["inputs"]
    assert inputs["responses_recommending_target_brand"] == 1
    assert inputs["total_responses"] == 3
    assert inputs["evidence_response_ids"] == [2]
    assert evidence["responses"][0]["brand_verdict"]["status"] == "NOT_RECOMMENDED"
    assert evidence["responses"][2]["brand_verdict"]["status"] == "NOT_MEASURED"
    assert evidence["recommendation_measurement"]["status"] == "PARTIAL"
    assert evidence["recommendation_measurement"]["rate_percent"] == 50.0
