from __future__ import annotations

import math
import re
from collections import defaultdict
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from research.models import Research, ResearchStatus, ResearchTask, Response
from yandex_intelligence.models import YandexIntelligenceSnapshot
from yandex_intelligence.ports import WebmasterEvidencePort
from yandex_intelligence.repository import YandexIntelligenceRepository
from yandex_intelligence.schemas import (
    YandexAiObservation,
    YandexIntelligenceRead,
    YandexOpportunity,
    YandexQueryMapItem,
    YandexQuerySeedsRead,
)


class YandexIntelligenceError(ValueError):
    pass


def _host(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return (parsed.hostname or "").casefold().removeprefix("www.")


class YandexIntelligenceService:
    VERSION = "1.0"

    def __init__(
        self,
        db: Session,
        webmaster: WebmasterEvidencePort,
        repository: YandexIntelligenceRepository | None = None,
    ) -> None:
        self.db = db
        self.webmaster = webmaster
        self.repository = repository or YandexIntelligenceRepository(db)

    def sync(self, organization_id: int) -> YandexIntelligenceRead:
        webmaster = self.webmaster.evidence(organization_id)
        ai = self._yandex_ai_observations(webmaster.host_url)
        query_map = self._query_map(webmaster.query_facts, ai)
        opportunities = self._opportunities(query_map)
        limitations = [
            "Выводы основаны на данных подтверждённого сайта в Яндекс Вебмастере "
            "и сохранённых ответах YandexGPT.",
            "Связь между поисковой позицией, страницей и рекомендацией ИИ является "
            "наблюдаемой корреляцией, а не доказанной причинностью.",
            "Данные раздела «Видимость в Алисе AI» не имитируются: нужен официальный "
            "экспорт или документированный API.",
        ]
        if webmaster.partial_errors:
            limitations.append(
                "Часть источников Вебмастера недоступна: "
                + ", ".join(sorted(webmaster.partial_errors))
                + "."
            )
        evidence_status = (
            "MEASURED" if query_map and ai else "PARTIAL" if query_map or ai else "NOT_MEASURED"
        )
        item = self.repository.save(
            YandexIntelligenceSnapshot(
                organization_id=organization_id,
                host_id=webmaster.host_id,
                host_url=webmaster.host_url,
                status="READY" if evidence_status != "NOT_MEASURED" else "INSUFFICIENT_DATA",
                evidence_status=evidence_status,
                webmaster_evidence=webmaster.model_dump(mode="json"),
                yandex_ai_evidence=[value.model_dump(mode="json") for value in ai],
                query_map=[value.model_dump(mode="json") for value in query_map],
                opportunities=[value.model_dump(mode="json") for value in opportunities],
                limitations=limitations,
                algorithm_version=self.VERSION,
            )
        )
        return self._read(item)

    def latest(self, organization_id: int) -> YandexIntelligenceRead:
        item = self.repository.latest(organization_id)
        if item is None:
            raise YandexIntelligenceError("Синхронизация Яндекс Intelligence ещё не выполнялась")
        return self._read(item)

    def query_seeds(
        self, organization_id: int, website_url: str | None = None
    ) -> YandexQuerySeedsRead:
        item = self.repository.latest(organization_id)
        if item is None:
            raise YandexIntelligenceError("Сначала синхронизируйте данные Яндекс Вебмастера")
        if website_url and _host(website_url) != _host(item.host_url):
            raise YandexIntelligenceError("Выбранный сайт не совпадает с сайтом исследования")
        candidates = sorted(
            item.query_map,
            key=lambda value: (
                value.get("demand") or value.get("impressions") or 0,
                -(value.get("position") or 100),
            ),
            reverse=True,
        )
        queries = list(dict.fromkeys(value["query"] for value in candidates if value.get("query")))[
            :12
        ]
        return YandexQuerySeedsRead(
            host_url=item.host_url,
            queries=queries,
            evidence_status=item.evidence_status,
            snapshot_id=item.id,
        )

    def _yandex_ai_observations(self, host_url: str) -> list[YandexAiObservation]:
        researches = list(
            self.db.scalars(
                select(Research)
                .where(Research.status == ResearchStatus.COMPLETED)
                .order_by(Research.created_at.desc())
                .limit(30)
            )
        )
        matching = [
            item
            for item in researches
            if _host(str(item.metadata_payload.get("website_url", ""))) == _host(host_url)
        ][:5]
        if not matching:
            return []
        rows = self.db.execute(
            select(Response, ResearchTask)
            .join(ResearchTask, Response.research_task_id == ResearchTask.id)
            .where(
                ResearchTask.research_id.in_([item.id for item in matching]),
                Response.provider.in_(["yandex", "yandexgpt"]),
            )
        ).all()
        research_by_id = {item.id: item for item in matching}
        observations = []
        for response, task in rows:
            research = research_by_id[task.research_id]
            brand = str(research.metadata_payload.get("brand", "")).strip()
            content = response.content or ""
            lowered = content.casefold()
            citations = re.findall(r"https?://[^\s)\]}>]+", content)
            observations.append(
                YandexAiObservation(
                    research_id=research.id,
                    response_id=response.id,
                    query=task.query,
                    brand=brand,
                    mentioned=bool(brand and brand.casefold() in lowered),
                    recommended=bool(
                        brand
                        and brand.casefold() in lowered
                        and any(word in lowered for word in ("рекоменд", "совету", "выбор"))
                    ),
                    citation_domains=list(
                        dict.fromkeys(_host(url) for url in citations if _host(url))
                    ),
                    observed_at=response.finished_at,
                )
            )
        return observations

    @staticmethod
    def _query_map(facts, ai: list[YandexAiObservation]) -> list[YandexQueryMapItem]:
        grouped: dict[tuple[str, str | None], list] = defaultdict(list)
        for fact in facts:
            grouped[(fact.query.strip(), fact.url)].append(fact)
        ai_by_query: dict[str, list[YandexAiObservation]] = defaultdict(list)
        for item in ai:
            ai_by_query[item.query.casefold().strip()].append(item)
        result = []
        for (query, url), rows in grouped.items():
            observations = ai_by_query.get(query.casefold(), [])
            result.append(
                YandexQueryMapItem(
                    query=query,
                    url=url,
                    impressions=YandexIntelligenceService._aggregate(rows, "impressions"),
                    clicks=YandexIntelligenceService._aggregate(rows, "clicks"),
                    ctr=YandexIntelligenceService._aggregate(rows, "ctr", average=True),
                    position=YandexIntelligenceService._aggregate(rows, "position", average=True),
                    demand=YandexIntelligenceService._aggregate(rows, "demand"),
                    yandex_ai_checked=bool(observations),
                    brand_mentioned=(
                        any(item.mentioned for item in observations) if observations else None
                    ),
                    evidence_status="MEASURED" if observations else "WEBMASTER_ONLY",
                )
            )
        return sorted(result, key=lambda item: item.demand or item.impressions or 0, reverse=True)

    @staticmethod
    def _aggregate(rows, field: str, *, average: bool = False) -> float | None:
        values = [getattr(item, field) for item in rows if getattr(item, field) is not None]
        if not values:
            return None
        value = sum(values) / len(values) if average else sum(values)
        return round(value, 4)

    @staticmethod
    def _opportunities(items: list[YandexQueryMapItem]) -> list[YandexOpportunity]:
        demand_max = max((item.demand or item.impressions or 0 for item in items), default=0)
        result = []
        for item in items:
            demand = item.demand or item.impressions or 0
            demand_signal = math.log1p(demand) / math.log1p(demand_max) if demand_max else 0
            position_gap = (
                1.0
                if item.position is None and demand
                else min(max(((item.position or 3) - 3) / 47, 0), 1)
            )
            ctr = item.ctr
            ctr_gap = min(max((5 - ctr) / 5, 0), 1) if ctr is not None else 0.5
            ai_gap = (
                1.0
                if item.brand_mentioned is False
                else 0.65
                if item.brand_mentioned is None
                else 0
            )
            score = round(
                100 * (0.3 * demand_signal + 0.25 * position_gap + 0.15 * ctr_gap + 0.3 * ai_gap), 1
            )
            if score < 35:
                continue
            priority = "P0" if score >= 75 else "P1" if score >= 55 else "P2"
            problem = (
                "YandexGPT не упомянул бренд по измеренному запросу"
                if item.brand_mentioned is False
                else "Запрос ещё не проверен в YandexGPT"
                if item.brand_mentioned is None
                else "Страница недостаточно заметна в органической выдаче"
            )
            action = (
                f"Доработать страницу {item.url}: дать прямой ответ на запрос «{item.query}», "
                "добавить проверяемые характеристики, авторство, дату обновления "
                "и независимые источники."
                if item.url
                else f"Создать отдельную экспертную страницу под запрос «{item.query}» "
                "и включить её в Sitemap."
            )
            impressions = item.impressions if item.impressions is not None else "нет данных"
            demand_value = item.demand if item.demand is not None else "нет данных"
            position = item.position if item.position is not None else "не определена"
            mention = item.brand_mentioned if item.brand_mentioned is not None else "не измерено"
            result.append(
                YandexOpportunity(
                    priority=priority,
                    priority_score=score,
                    query=item.query,
                    problem=problem,
                    evidence=(
                        f"Показы: {impressions}; спрос: {demand_value}; позиция: {position}; "
                        f"упоминание YandexGPT: {mention}."
                    ),
                    affected_metric="Yandex visibility / AI recommendation",
                    action=action,
                    target_url=item.url,
                    expected_range="Измеряется повторно; гарантированный прирост не заявляется",
                    confidence="HIGH" if item.evidence_status == "MEASURED" else "MEDIUM",
                    effort="MEDIUM",
                    duration="2–6 недель до повторного измерения",
                    verification=(
                        f"Повторить неизменный запрос «{item.query}» в YandexGPT "
                        "и сравнить позицию/упоминание."
                    ),
                )
            )
        return sorted(result, key=lambda item: item.priority_score, reverse=True)[:20]

    @staticmethod
    def _read(item: YandexIntelligenceSnapshot) -> YandexIntelligenceRead:
        return YandexIntelligenceRead(
            id=item.id,
            organization_id=item.organization_id,
            host_id=item.host_id,
            host_url=item.host_url,
            status=item.status,
            evidence_status=item.evidence_status,
            webmaster=item.webmaster_evidence,
            yandex_ai=[
                YandexAiObservation.model_validate(value) for value in item.yandex_ai_evidence
            ],
            query_map=[YandexQueryMapItem.model_validate(value) for value in item.query_map],
            opportunities=[YandexOpportunity.model_validate(value) for value in item.opportunities],
            limitations=item.limitations,
            algorithm_version=item.algorithm_version,
            created_at=item.created_at,
        )


class YandexIntelligenceQuerySource:
    """Read-only public source used by the research orchestrator."""

    def __init__(self, db: Session) -> None:
        self.repository = YandexIntelligenceRepository(db)

    def queries(
        self, organization_id: int, website_url: str, limit: int = 8
    ) -> tuple[int, list[str]]:
        item = self.repository.latest(organization_id)
        if item is None or _host(item.host_url) != _host(website_url):
            return 0, []
        candidates = sorted(
            item.query_map,
            key=lambda value: (
                value.get("demand") or value.get("impressions") or 0,
                -(value.get("position") or 100),
            ),
            reverse=True,
        )
        return item.id, list(
            dict.fromkeys(value["query"] for value in candidates if value.get("query"))
        )[:limit]
