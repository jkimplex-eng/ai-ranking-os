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
    assert result["observations"][0]["brand_verdict"]["status"] == "RECOMMENDED"
    assert result["source_patterns"][0]["domain"] == "app.разуммаркета.рф"
    assert result["source_patterns"][0]["used_in_answers"] == 1


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


def test_unselected_source_does_not_count_as_target_citation() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {"content": "Другой сервис подходит для задачи."},
                "sources": [
                    {
                        "url": "https://app.разуммаркета.рф/about.html",
                        "title": "О платформе",
                        "used": False,
                    }
                ],
            },
        )

    service = YandexGenerativeEvidenceService(
        httpx.Client(transport=httpx.MockTransport(handler))
    )
    result = service.measure(
        credential="secret",
        auth_type="API_KEY",
        folder_id="folder",
        queries=["какой сервис выбрать"],
        brand="Разум рынка",
        website_url="https://app.разуммаркета.рф",
    )

    assert result["target_citation_count"] == 0
    assert result["observations"][0]["target_cited"] is False
    assert result["source_patterns"] == []


def test_generative_evidence_does_not_count_negative_or_other_brand_recommendation() -> None:
    responses = iter(
        [
            "Не рекомендую Разум рынка, лучше выбрать Другой сервис.",
            "Разум рынка упомянут, но рекомендуем Другой сервис.",
        ]
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": next(responses)}, "sources": []})

    service = YandexGenerativeEvidenceService(
        httpx.Client(transport=httpx.MockTransport(handler))
    )
    result = service.measure(
        credential="secret",
        auth_type="API_KEY",
        folder_id="folder",
        queries=["первый запрос", "второй запрос"],
        brand="Разум рынка",
    )

    assert result["mention_count"] == 2
    assert result["recommendation_count"] == 0
    assert [item["brand_verdict"]["status"] for item in result["observations"]] == [
        "NOT_RECOMMENDED",
        "MENTIONED",
    ]


def test_prepare_queries_disambiguates_geo_for_consumer_measurement() -> None:
    prepared = YandexGenerativeEvidenceService.prepare_queries(
        ["geo продвижение заказать", "geo продвижение в нейросетях заказать"]
    )

    assert prepared == [
        "geo продвижение заказать в нейросетях (Generative Engine Optimization)",
        "geo продвижение в нейросетях заказать",
    ]


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
