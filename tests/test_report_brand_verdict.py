from types import SimpleNamespace

from product.service import FinalReportService
from research.models import ResponseProcessingStatus


def _response(
    response_id: int,
    content: str,
    status=ResponseProcessingStatus.PROCESSED,
    prompt="Какой бренд выбрать?",
):
    return SimpleNamespace(
        id=response_id, content=content, processing_status=status,
        provider="yandex", model="test", prompt=prompt,
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


def test_report_shows_offered_option_without_counting_explicit_recommendation():
    research = SimpleNamespace(
        id=2, title="Skillbox", metadata_payload={"brand": "Skillbox"},
        total_tasks=1, tasks=[],
    )
    base = SimpleNamespace(
        responses=[_response(
            436,
            "Вот некоторые из них:\n1. Skillbox — курсы дизайна\n"
            "2. Netology — курсы маркетинга",
        )],
        entities=[], citations=[], recommendations=[],
    )
    evidence = FinalReportService._explainability(research, base, None)
    assert evidence["recommendation_measurement"]["recommended_responses"] == 0
    assert evidence["option_measurement"]["option_responses"] == 1
    assert evidence["option_measurement"]["evidence_response_ids"] == [436]
    assert evidence["responses"][0]["brand_verdict"]["status"] == "PROPOSED_AS_OPTION"


def test_historical_score_is_not_silently_relabelled_as_current_methodology():
    research = SimpleNamespace(
        id=3, title="Skillbox", metadata_payload={"brand": "Skillbox"},
        total_tasks=1, tasks=[],
    )
    base = SimpleNamespace(
        responses=[_response(
            436, "Вот некоторые из них:\n1. Skillbox — курсы\n2. Netology — курсы"
        )],
        entities=[], citations=[], recommendations=[],
    )
    evidence = FinalReportService._explainability(
        research, base, {
            "version": "3.0-brand-verdict-1.1",
            "mention_score": 100,
            "recommendation_score": 0,
            "citation_score": 0,
            "coverage_score": 100,
            "confidence_score": 20,
        }
    )
    assert evidence["methodology_version"] == "3.0-brand-verdict-1.1"
    assert evidence["evidence_methodology_version"] == "4.0-brand-verdict-1.3"
    assert evidence["historical_score_warning"]


def test_report_excludes_branded_controls_from_visibility_numerator_and_denominator():
    research = SimpleNamespace(
        id=4, title="Signal", metadata_payload={"brand": "Signal"},
        total_tasks=2, tasks=[],
    )
    base = SimpleNamespace(
        responses=[
            _response(1, "Signal — приложение для сообщений.", prompt="Что делает Signal?"),
            _response(2, "Есть несколько сервисов для GEO.", prompt="Какие сервисы для GEO?"),
        ],
        entities=[], citations=[], recommendations=[],
    )
    evidence = FinalReportService._explainability(research, base, None)
    assert evidence["metrics"]["mention_score"]["inputs"]["mentioned_responses"] == 0
    assert evidence["metrics"]["mention_score"]["inputs"]["total_responses"] == 1
    assert evidence["sample_scope"]["excluded_branded_response_ids"] == [1]
    assert evidence["responses"][0]["counts_toward_visibility"] is False
    assert evidence["responses"][1]["counts_toward_visibility"] is True
