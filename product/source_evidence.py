"""Descriptive, system-separated source evidence; never a causal ranking model."""

from collections import defaultdict
from typing import Any


def source_evidence(patterns: dict[str, Any]) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in patterns.get("query_matrix", []):
        groups[(row["provider"], row["model"])].append(row)
    resources = []
    for (provider, model), rows in sorted(groups.items()):
        domains = sorted({domain for row in rows for domain in row.get("sources", [])})
        for domain in domains:
            with_source = [row for row in rows if domain in row.get("sources", [])]
            without_source = [row for row in rows if domain not in row.get("sources", [])]
            mentioned_with = sum(bool(row["mentioned"]) for row in with_source)
            mentioned_without = sum(bool(row["mentioned"]) for row in without_source)
            resources.append(
                {
                    "resource": domain,
                    "provider": provider,
                    "model": model,
                    "with_source": len(with_source),
                    "without_source": len(without_source),
                    "mentioned_with": mentioned_with,
                    "mentioned_without": mentioned_without,
                    "mention_rate_with": round(100 * mentioned_with / len(with_source), 1),
                    "mention_rate_without": round(100 * mentioned_without / len(without_source), 1)
                    if without_source
                    else None,
                    "status": "DESCRIPTIVE_ONLY"
                    if min(len(with_source), len(without_source)) >= 3
                    else "INSUFFICIENT_COMPARISON",
                    "response_ids": [row["response_id"] for row in with_source],
                    "queries": sorted({row["query"] for row in with_source}),
                    "urls": sorted(
                        {
                            url
                            for row in with_source
                            for url in row.get("source_urls", [])
                            if _host(url) == domain
                        }
                    ),
                }
            )
    resources.sort(
        key=lambda row: (-row["with_source"], row["resource"], row["provider"], row["model"])
    )
    return {
        "version": "1.0",
        "resources": resources,
        "successful_responses": sum(len(rows) for rows in groups.values()),
        "excluded_responses": patterns.get("sample", {}).get("excluded_responses", 0),
        "method": (
            "Для каждой модели отдельно считаем успешные ответы со ссылкой на "
            "ресурс и без неё; в каждой группе считаем упоминания бренда. Один "
            "ответ учитывается один раз на ресурс."
        ),
        "limitation": (
            "Это описательная статистика одного исследования, не критерии "
            "закрытого алгоритма. Вопросы в группах могут различаться. "
            "Упоминание не равно рекомендации; связь не доказывает влияние "
            "ресурса."
        ),
        "next_step": (
            "Повторять одинаковые вопросы в той же системе и регионе. Сохранять "
            "даты публикаций и изменения страниц. Проверять гипотезы на "
            "последующих исследованиях, не смешивая разные модели."
        ),
    }


def _host(url: str) -> str | None:
    from urllib.parse import urlparse

    try:
        return urlparse(url).hostname
    except ValueError:
        return None
