import base64
import json

import httpx

from yandex_wordstat.search_evidence import YandexSearchEvidenceService


def test_search_evidence_parses_and_ranks_observed_domains() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        query = json.loads(request.read())["query"]["queryText"]
        if "первый сервис" in query:
            docs = """
              <group><doc><url>https://vc.ru/one</url><title>Первый материал</title></doc></group>
              <group><doc><url>https://example.ru/a</url>
              <title>Другой материал</title></doc></group>
            """
        else:
            docs = """
              <group><doc><url>https://vc.ru/two</url><title>Второй материал</title></doc></group>
            """
        xml = (
            "<yandexsearch><response><results><grouping>"
            f"{docs}"
            "</grouping></results></response></yandexsearch>"
        )
        return httpx.Response(
            200,
            json={"rawData": base64.b64encode(xml.encode()).decode()},
        )

    service = YandexSearchEvidenceService(
        httpx.Client(transport=httpx.MockTransport(handler))
    )
    result = service.discover(
        credential="secret",
        auth_type="API_KEY",
        folder_id="folder",
        queries=["первый сервис", "второй сервис"],
    )

    assert len(requests) == 2
    assert all(request.headers["Authorization"] == "Api-key secret" for request in requests)
    assert result["status"] == "MEASURED"
    assert result["queries_measured"] == 2
    assert result["resources"][0]["domain"] == "vc.ru"
    assert result["resources"][0]["query_count"] == 2
    assert result["resources"][0]["search_presence_score"] == 100.0
    assert result["resources"][0]["evidence_status"] == "OBSERVED_YANDEX_SEARCH"
    assert "не ссылки Алисы" in result["limitations"][0]


def test_search_query_selection_prefers_commercial_intent_and_caps_calls() -> None:
    selected = YandexSearchEvidenceService.select_queries(
        [
            "geo продвижение",
            "теория geo",
            "компании geo продвижения",
            "услуги geo продвижения",
            "сколько стоит geo продвижение",
            "geo продвижение заказать",
            "обзор сервисов geo",
            "лишний запрос",
        ]
    )

    assert selected == [
        "компании geo продвижения",
        "услуги geo продвижения",
        "сколько стоит geo продвижение",
        "geo продвижение заказать",
        "обзор сервисов geo",
    ]
