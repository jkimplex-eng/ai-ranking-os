from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx


class YandexSearchEvidenceError(ValueError):
    pass


class YandexSearchEvidenceService:
    """Collect observed Yandex web results without claiming Alice causality."""

    BASE_URL = "https://searchapi.api.cloud.yandex.net/v2/web/search"
    VERSION = "yandex-search-evidence-1.0"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=30)

    def discover(
        self,
        *,
        credential: str,
        auth_type: str,
        folder_id: str,
        queries: list[str],
        region_id: int = 225,
        results_per_query: int = 10,
    ) -> dict[str, Any]:
        selected = self.select_queries(queries, limit=5)
        observations: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        for query in selected:
            try:
                rows = self._search(
                    credential=credential,
                    auth_type=auth_type,
                    folder_id=folder_id,
                    query=query,
                    region_id=region_id,
                    results_per_query=results_per_query,
                )
            except (httpx.HTTPError, ValueError, ET.ParseError) as error:
                failures.append({"query": query, "error": self._safe_error(error)})
                continue
            observations.extend(rows)
        return self._report(selected, observations, failures, region_id)

    def _search(
        self,
        *,
        credential: str,
        auth_type: str,
        folder_id: str,
        query: str,
        region_id: int,
        results_per_query: int,
    ) -> list[dict[str, Any]]:
        response = self.client.post(
            self.BASE_URL,
            headers={
                "Authorization": (
                    f"Api-key {credential}"
                    if auth_type == "API_KEY"
                    else f"Bearer {credential}"
                )
            },
            json={
                "query": {
                    "searchType": "SEARCH_TYPE_RU",
                    "queryText": query[:400],
                    "familyMode": "FAMILY_MODE_MODERATE",
                    "page": "0",
                    "fixTypoMode": "FIX_TYPO_MODE_ON",
                },
                "groupSpec": {
                    "groupMode": "GROUP_MODE_FLAT",
                    "groupsOnPage": str(max(1, min(results_per_query, 100))),
                    "docsInGroup": "1",
                },
                "region": str(region_id),
                "l10n": "LOCALIZATION_RU",
                "folderId": folder_id,
                "responseFormat": "FORMAT_XML",
            },
        )
        response.raise_for_status()
        raw_data = response.json().get("rawData")
        if not isinstance(raw_data, str) or not raw_data:
            raise YandexSearchEvidenceError("Yandex Search API did not return rawData")
        root = ET.fromstring(base64.b64decode(raw_data))
        rows = []
        for position, document in enumerate(root.findall(".//doc"), start=1):
            url = (document.findtext("url") or "").strip()
            domain = (urlparse(url).hostname or "").casefold().removeprefix("www.")
            if not url or not domain:
                continue
            title_node = document.find("title")
            title = "".join(title_node.itertext()).strip() if title_node is not None else domain
            rows.append(
                {
                    "query": query,
                    "position": position,
                    "url": url,
                    "domain": domain,
                    "title": title,
                }
            )
        return rows

    @classmethod
    def _report(
        cls,
        queries: list[str],
        observations: list[dict[str, Any]],
        failures: list[dict[str, str]],
        region_id: int,
    ) -> dict[str, Any]:
        grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in observations:
            grouped[item["domain"]].append(item)
        measured_queries = len({item["query"] for item in observations})
        denominator = max(measured_queries, 1)
        resources = []
        for domain, evidence in grouped.items():
            query_count = len({item["query"] for item in evidence})
            reciprocal_rank_sum = sum(1 / int(item["position"]) for item in evidence)
            resources.append(
                {
                    "domain": domain,
                    "query_count": query_count,
                    "query_coverage_percent": round(query_count / denominator * 100, 1),
                    "best_position": min(int(item["position"]) for item in evidence),
                    "search_presence_score": round(reciprocal_rank_sum / denominator * 100, 1),
                    "evidence_status": "OBSERVED_YANDEX_SEARCH",
                    "confidence": (
                        "HIGH"
                        if query_count >= 3
                        else "MEDIUM"
                        if query_count >= 2
                        else "LOW"
                    ),
                    "action": (
                        "Проверить редакционные требования площадки и подготовить материал, "
                        "закрывающий наблюдаемые запросы."
                    ),
                    "evidence": sorted(
                        evidence, key=lambda item: (item["query"], item["position"])
                    ),
                }
            )
        resources.sort(
            key=lambda item: (
                -item["query_count"],
                -item["search_presence_score"],
                item["best_position"],
                item["domain"],
            )
        )
        return {
            "version": cls.VERSION,
            "status": "MEASURED" if measured_queries else "NOT_MEASURED",
            "region_id": region_id,
            "queries_requested": queries,
            "queries_measured": measured_queries,
            "observations": len(observations),
            "failures": failures,
            "resources": resources,
            "formula": (
                "search_presence_score = 100 × Σ(1 / позиция результата) / "
                "число успешно проверенных запросов"
            ),
            "captured_at": datetime.now(UTC).isoformat(),
            "limitations": [
                "Это позиции в Яндекс Поиске, а не ссылки Алисы или YandexGPT.",
                "Высокая позиция показывает наблюдаемую поисковую видимость, но не доказывает "
                "влияние площадки на рекомендации ИИ.",
                "Перед публикацией нужно проверить редакционную доступность, стоимость и "
                "соответствие аудитории; система не выдаёт непроверенную площадку за гарантию.",
            ],
        }

    @staticmethod
    def select_queries(queries: list[str], limit: int = 5) -> list[str]:
        intent_markers = (
            "сервис",
            "компан",
            "заказать",
            "услуг",
            "стоимость",
            "сколько стоит",
            "рейтинг",
            "обзор",
            "статья",
            "где ",
        )
        cleaned = list(dict.fromkeys(query.strip() for query in queries if query.strip()))
        ranked = sorted(
            enumerate(cleaned),
            key=lambda row: (
                0 if any(marker in row[1].casefold() for marker in intent_markers) else 1,
                row[0],
            ),
        )
        return [query for _, query in ranked[:limit]]

    @staticmethod
    def _safe_error(error: Exception) -> str:
        if isinstance(error, httpx.HTTPStatusError):
            return f"Yandex Search API HTTP {error.response.status_code}"
        if isinstance(error, httpx.TimeoutException):
            return "Yandex Search API timeout"
        return "Yandex Search API response could not be parsed"
