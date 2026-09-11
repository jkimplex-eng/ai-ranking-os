from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from yandex_wordstat.search_evidence import YandexSearchEvidenceService


class YandexGenerativeEvidenceService:
    """Measure Yandex generative-search answers without calling them consumer Alice."""

    BASE_URL = "https://searchapi.api.cloud.yandex.net/v2/gen/search"
    VERSION = "yandex-generative-search-1.0"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=60)

    def measure(
        self,
        *,
        credential: str,
        auth_type: str,
        folder_id: str,
        queries: list[str],
        brand: str,
        website_url: str | None = None,
    ) -> dict[str, Any]:
        selected = self.prepare_queries(queries)
        observations: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        target_domain = self._domain(website_url)
        for query in selected:
            try:
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
                        "messages": [{"content": query, "role": "ROLE_USER"}],
                        "folderId": folder_id,
                        "fixMisspell": True,
                        "enableRichStructuredAnswer": True,
                        "getPartialResults": False,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, list):
                    payload = next(
                        (item for item in reversed(payload) if isinstance(item, dict)),
                        {},
                    )
                if not isinstance(payload, dict):
                    raise ValueError("Unexpected Yandex GenSearch response")
                content = str((payload.get("message") or {}).get("content") or "")
                sources = [
                    {
                        "url": str(item.get("url") or ""),
                        "title": str(item.get("title") or ""),
                        "used": bool(item.get("used", False)),
                    }
                    for item in payload.get("sources", [])
                    if isinstance(item, dict) and item.get("url")
                ]
                normalized = content.casefold()
                brand_mentioned = brand.strip().casefold() in normalized
                target_cited = bool(
                    target_domain
                    and any(target_domain == self._domain(item["url"]) for item in sources)
                )
                recommendation_markers = ("рекоменду", "совету", "подойд", "выбрать")
                observations.append(
                    {
                        "query": query,
                        "answer": content,
                        "brand_mentioned": brand_mentioned,
                        "brand_recommended": brand_mentioned
                        and any(marker in normalized for marker in recommendation_markers),
                        "target_cited": target_cited,
                        "sources": sources,
                        "search_queries": payload.get("searchQueries", []),
                    }
                )
            except (httpx.HTTPError, ValueError, TypeError) as error:
                failures.append({"query": query, "error": self._safe_error(error)})
        return self._report(selected, observations, failures)

    @classmethod
    def _report(
        cls,
        queries: list[str],
        observations: list[dict[str, Any]],
        failures: list[dict[str, str]],
    ) -> dict[str, Any]:
        measured = len(observations)
        mentions = sum(bool(item["brand_mentioned"]) for item in observations)
        recommendations = sum(bool(item["brand_recommended"]) for item in observations)
        citations = sum(bool(item["target_cited"]) for item in observations)
        denominator = max(measured, 1)
        score = round(
            100
            * (
                0.6 * mentions / denominator
                + 0.25 * recommendations / denominator
                + 0.15 * citations / denominator
            ),
            1,
        )
        grouped_sources: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for observation in observations:
            for source in observation["sources"]:
                if not source["used"]:
                    continue
                domain = cls._domain(source["url"])
                if domain:
                    grouped_sources[domain].append(
                        {
                            "query": observation["query"],
                            "url": source["url"],
                            "title": source["title"],
                        }
                    )
        source_patterns = [
            {
                "domain": domain,
                "used_in_answers": len({item["query"] for item in evidence}),
                "coverage_percent": round(
                    len({item["query"] for item in evidence}) / denominator * 100, 1
                ),
                "confidence": (
                    "HIGH"
                    if len({item["query"] for item in evidence}) >= 3
                    else "MEDIUM"
                    if len({item["query"] for item in evidence}) >= 2
                    else "LOW"
                ),
                "evidence": evidence,
                "interpretation": (
                    "Яндекс использовал этот домен при формировании генеративного ответа. "
                    "Это основание изучить формат материалов, но не доказательство, что "
                    "на площадке можно свободно опубликоваться."
                ),
            }
            for domain, evidence in grouped_sources.items()
        ]
        source_patterns.sort(
            key=lambda item: (-item["used_in_answers"], item["domain"])
        )
        return {
            "version": cls.VERSION,
            "status": "MEASURED" if measured else "NOT_MEASURED",
            "queries_requested": queries,
            "queries_measured": measured,
            "mention_count": mentions,
            "recommendation_count": recommendations,
            "target_citation_count": citations,
            "visibility_score": score if measured else None,
            "formula": (
                "100 × (0.60 × доля упоминаний + 0.25 × доля рекомендаций + "
                "0.15 × доля ответов со ссылкой на сайт бренда)"
            ),
            "observations": observations,
            "source_patterns": source_patterns,
            "failures": failures,
            "captured_at": datetime.now(UTC).isoformat(),
            "evidence_status": "OBSERVED_YANDEX_GENERATIVE_SEARCH",
            "limitations": [
                "Это официальный генеративный поиск Yandex Search API, а не запись экрана "
                "пользовательской Алисы.",
                "Интерфейс, персонализация и экспериментальные варианты ответа Алисы могут "
                "отличаться.",
                "Рекомендация определяется прозрачным языковым правилом и требует просмотра "
                "исходного ответа.",
            ],
        }

    @staticmethod
    def _domain(url: str | None) -> str:
        if not url:
            return ""
        value = url if "://" in url else f"https://{url}"
        return (urlparse(value).hostname or "").casefold().removeprefix("www.")

    @staticmethod
    def prepare_queries(queries: list[str], limit: int = 5) -> list[str]:
        """Disambiguate GEO while preserving Wordstat demand as the source."""
        selected = YandexSearchEvidenceService.select_queries(queries, limit=limit)
        context_markers = ("нейросет", " ии", " ai", "yandexgpt", "алис", "generative")
        prepared = []
        for query in selected:
            normalized = query.casefold()
            if ("geo" in normalized or "гео" in normalized) and not any(
                marker in normalized for marker in context_markers
            ):
                prepared.append(
                    f"{query} в нейросетях (Generative Engine Optimization)"
                )
            else:
                prepared.append(query)
        return prepared

    @staticmethod
    def _safe_error(error: Exception) -> str:
        if isinstance(error, httpx.HTTPStatusError):
            return f"Yandex GenSearch API HTTP {error.response.status_code}"
        if isinstance(error, httpx.TimeoutException):
            return "Yandex GenSearch API timeout"
        return "Yandex GenSearch API response could not be parsed"
