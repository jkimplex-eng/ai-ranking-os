import httpx

from yandex_wordstat.generative_evidence import YandexGenerativeEvidenceService


def test_generative_evidence_measures_brand_and_target_citation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Api-key secret"
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": "Рекомендуем Разум рынка как один из подходящих сервисов."
                },
                "sources": [
                    {
                        "url": "https://app.разуммаркета.рф/about.html",
                        "title": "О платформе",
                        "used": True,
                    }
                ],
                "searchQueries": [{"text": "сервис GEO"}],
            },
        )

    service = YandexGenerativeEvidenceService(
        httpx.Client(transport=httpx.MockTransport(handler))
    )
    result = service.measure(
        credential="secret",
        auth_type="API_KEY",
        folder_id="folder",
        queries=["какой сервис GEO выбрать"],
        brand="Разум рынка",
        website_url="https://app.разуммаркета.рф",
    )

    assert result["status"] == "MEASURED"
    assert result["mention_count"] == 1
    assert result["recommendation_count"] == 1
    assert result["target_citation_count"] == 1
    assert result["visibility_score"] == 100.0
    assert result["evidence_status"] == "OBSERVED_YANDEX_GENERATIVE_SEARCH"


def test_generative_evidence_does_not_infer_a_missing_brand() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {"content": "Можно сравнить несколько сервисов."},
                "sources": [],
            },
        )

    service = YandexGenerativeEvidenceService(
        httpx.Client(transport=httpx.MockTransport(handler))
    )
    result = service.measure(
        credential="secret",
        auth_type="API_KEY",
        folder_id="folder",
        queries=["какой сервис GEO выбрать"],
        brand="Разум рынка",
    )

    assert result["mention_count"] == 0
    assert result["recommendation_count"] == 0
    assert result["target_citation_count"] == 0
    assert result["visibility_score"] == 0.0


def test_generative_evidence_accepts_a_list_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {"message": {"content": "Промежуточный ответ"}},
                {
                    "message": {"content": "Разум рынка упомянут в итоговом ответе."},
                    "sources": [],
                },
            ],
        )

    service = YandexGenerativeEvidenceService(
        httpx.Client(transport=httpx.MockTransport(handler))
    )
    result = service.measure(
        credential="secret",
        auth_type="API_KEY",
        folder_id="folder",
        queries=["какой сервис GEO выбрать"],
        brand="Разум рынка",
    )

    assert result["mention_count"] == 1
