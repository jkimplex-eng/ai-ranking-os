"""Publication candidates built only from saved Yandex generative-search evidence."""

from typing import Any

from geo_platforms.models import GeoPlatform


def observed_candidate(
    *, organization_id: int, research_id: int, source: dict[str, Any]
) -> GeoPlatform | None:
    domain = str(source.get("domain") or "").strip().casefold()
    proof = source.get("evidence")
    if not domain or not isinstance(proof, list):
        return None
    observations = [
        {
            "query": str(item.get("query") or ""),
            "url": str(item.get("url") or ""),
            "title": str(item.get("title") or ""),
        }
        for item in proof
        if isinstance(item, dict) and item.get("query") and item.get("url")
    ]
    if not observations:
        return None
    query = observations[0]["query"]
    return GeoPlatform(
        organization_id=organization_id,
        name=domain,
        domain=domain,
        platform_type="PUBLICATION",
        category="OBSERVED_YANDEX_SOURCE",
        country="GLOBAL",
        language="ALL",
        source="YANDEX_SEARCH_GENERATIVE",
        source_reference=f"research:{research_id}",
        ai_engines=["YANDEX_SEARCH_GENERATIVE"],
        evidence={
            "status": "OBSERVED",
            "research_id": research_id,
            "used_in_answers": source.get("used_in_answers", 0),
            "coverage_percent": source.get("coverage_percent", 0),
            "confidence": source.get("confidence", "LOW"),
            "urls": [item["url"] for item in observations],
            "source_observations": observations,
            "why_observed": source.get("interpretation", ""),
            "suggested_topic": f"Материал, который полно отвечает на запрос: «{query}».",
            "publication_task": {
                "status": "OBSERVED",
                "owner": "",
                "due_date": "",
                "content_format": "Экспертная статья",
                "publication_url": "",
                "editorial_status": "NOT_CHECKED",
                "editorial_rules_url": "",
                "editorial_note": "",
            },
        },
    )
