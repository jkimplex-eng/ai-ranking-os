"""Inspectable, descriptive evidence for sources observed in AI answers.

This module deliberately does not infer or claim the private ranking criteria of
Yandex or any other AI system.  It records what was observed in the sampled
answers and in publicly available HTML at the time of inspection.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from geo_site_audit.service import _AuditParser, PublicSiteFetcher, SiteAuditError
from research.models import ExtractedCitation, Research, ResearchTask, Response


class SourceInspectionError(ValueError):
    pass


class SourceInspectionService:
    VERSION = "source_evidence_v1.0"
    MAX_SOURCES = 10
    LIMITATION = (
        "Отчёт показывает наблюдаемые ссылки и публичные признаки HTML на дату проверки. "
        "Он не раскрывает закрытый алгоритм Яндекса и не доказывает, что любой отдельный "
        "признак стал причиной рекомендации."
    )

    def __init__(self, db: Session) -> None:
        self.db = db
        self.fetcher = PublicSiteFetcher()

    def inspect(self, research_id: int) -> dict[str, Any]:
        research = self.db.get(Research, research_id)
        if research is None:
            raise SourceInspectionError("Исследование не найдено")
        citations = list(
            self.db.scalars(
                select(ExtractedCitation)
                .join(Response, ExtractedCitation.response_id == Response.id)
                .join(ResearchTask, Response.research_task_id == ResearchTask.id)
                .where(ResearchTask.research_id == research_id)
            )
        )
        grouped = self._group(citations)
        target = self._target_features(str(research.metadata_payload.get("website_url") or ""))
        sources = [
            self._inspect_source(domain, evidence, target)
            for domain, evidence in sorted(
                grouped.items(), key=lambda pair: (-len(pair[1]["response_ids"]), pair[0])
            )[: self.MAX_SOURCES]
        ]
        return {
            "version": self.VERSION,
            "research_id": research_id,
            "sample": {
                "observed_sources": len(grouped),
                "inspected_sources": len(sources),
                "citation_records": len(citations),
                "max_sources": self.MAX_SOURCES,
            },
            "target_site": target,
            "sources": sources,
            "method": (
                "Сначала группируем извлечённые ссылки по домену и сохраняем ответы, "
                "запросы, модели и URL. Затем ограниченно читаем публичную HTML-страницу "
                "каждого домена и сравниваем только измеримые признаки с официальным сайтом."
            ),
            "limitation": self.LIMITATION,
            "next_step": (
                "Сформулируйте гипотезу по наблюдаемому разрыву, внесите изменение на сайте "
                "или опубликуйте материал, затем повторите тот же Frozen Prompt Set. "
                "Изменение метрик будет наблюдением, а не автоматически доказанной причинностью."
            ),
        }

    @staticmethod
    def _group(citations: list[ExtractedCitation]) -> dict[str, dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"response_ids": set(), "queries": set(), "models": set(), "urls": set(), "titles": set()}
        )
        for citation in citations:
            url = str(citation.url or "")
            try:
                domain = (urlparse(url).hostname or "").casefold().removeprefix("www.")
            except ValueError:
                domain = ""
            if not domain:
                continue
            response = citation.response
            item = grouped[domain]
            item["response_ids"].add(response.id)
            item["queries"].add(response.prompt)
            item["models"].add(f"{response.provider}/{response.model}")
            item["urls"].add(url)
            if citation.title:
                item["titles"].add(citation.title)
        return grouped

    def _target_features(self, url: str) -> dict[str, Any]:
        if not url:
            return {"status": "NOT_MEASURED", "reason": "Официальный сайт не указан", "features": {}}
        try:
            final, html, status, _, content_type = self.fetcher.fetch(url)
            if status >= 400 or "html" not in content_type.casefold():
                raise SourceInspectionError(f"HTTP {status}")
            parser = _AuditParser()
            parser.feed(html)
            return {"status": "MEASURED", "url": final, "features": self._features(parser)}
        except (SiteAuditError, SourceInspectionError) as error:
            return {"status": "NOT_MEASURED", "reason": str(error), "features": {}}

    def _inspect_source(self, domain: str, evidence: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
        url = sorted(evidence["urls"])[0]
        facts: dict[str, Any]
        try:
            final, html, status, _, content_type = self.fetcher.fetch(url)
            if status >= 400 or "html" not in content_type.casefold():
                raise SourceInspectionError(f"HTTP {status}")
            parser = _AuditParser()
            parser.feed(html)
            facts = {"status": "MEASURED", "url": final, "features": self._features(parser)}
        except (SiteAuditError, SourceInspectionError) as error:
            facts = {"status": "NOT_MEASURED", "url": url, "reason": str(error), "features": {}}
        response_count = len(evidence["response_ids"])
        query_count = len(evidence["queries"])
        confidence = "HIGH" if response_count >= 5 and query_count >= 2 else "MEDIUM" if response_count >= 2 else "LOW"
        gaps = self._gaps(facts.get("features", {}), target.get("features", {}))
        return {
            "domain": domain,
            "observation": {
                "response_count": response_count,
                "query_count": query_count,
                "response_ids": sorted(evidence["response_ids"]),
                "queries": sorted(evidence["queries"]),
                "models": sorted(evidence["models"]),
                "urls": sorted(evidence["urls"]),
                "titles": sorted(evidence["titles"]),
                "confidence": confidence,
                "interpretation": (
                    f"Домен встречается в {response_count} ответах по {query_count} запросам "
                    "в этой выборке. Это наблюдение, а не установленная причина рекомендации."
                ),
            },
            "page": facts,
            "comparison_with_target": {
                "status": "AVAILABLE" if target.get("status") == "MEASURED" and facts["status"] == "MEASURED" else "PARTIAL",
                "source_has_target_lacks": gaps,
                "interpretation": (
                    "Это различия в публичной разметке и структуре одной страницы. Они полезны "
                    "для проверки гипотез, но не являются факторами ранжирования."
                ),
            },
        }

    @staticmethod
    def _features(parser: _AuditParser) -> dict[str, Any]:
        nodes = SourceInspectionService._json_nodes(parser.json_ld)
        types = sorted({str(item.get("@type")) for item in nodes if item.get("@type")})
        has_faq = any("FAQPage" in str(item.get("@type", "")) for item in nodes)
        has_author = bool(parser.meta.get("author")) or any(bool(item.get("author")) for item in nodes)
        has_date = any(
            parser.meta.get(key)
            for key in ("article:published_time", "date", "datepublished")
        ) or any(bool(item.get("datePublished") or item.get("dateModified")) for item in nodes)
        has_same_as = any(bool(item.get("sameAs")) for item in nodes)
        has_contact = any(
            item.get("contactPoint") or item.get("address") or "ContactPoint" in str(item.get("@type", ""))
            for item in nodes
        )
        return {
            "title": parser.title or None,
            "h1": parser.h1[:2],
            "description": parser.description or None,
            "schema_types": types,
            "has_faq_schema": has_faq,
            "has_author": has_author,
            "has_publication_date": has_date,
            "has_same_as": has_same_as,
            "has_contact_schema": has_contact,
        }

    @staticmethod
    def _json_nodes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            graph = item.get("@graph")
            if isinstance(graph, list):
                result.extend(node for node in graph if isinstance(node, dict))
            else:
                result.append(item)
        return result

    @staticmethod
    def _gaps(source: dict[str, Any], target: dict[str, Any]) -> list[dict[str, str]]:
        checks = [
            ("has_faq_schema", "FAQ-разметка", "Добавить FAQPage только для реальных вопросов и ответов."),
            ("has_author", "автор материала", "Указать автора и его роль на экспертных материалах."),
            ("has_publication_date", "дата публикации", "Указывать datePublished/dateModified для статей."),
            ("has_same_as", "подтверждённые профили sameAs", "Связать официальный сайт с реальными официальными профилями."),
            ("has_contact_schema", "ContactPoint или PostalAddress", "Добавить реальные контактные данные в JSON-LD."),
        ]
        return [
            {"signal": title, "action": action}
            for key, title, action in checks
            if source.get(key) is True and target.get(key) is not True
        ]
