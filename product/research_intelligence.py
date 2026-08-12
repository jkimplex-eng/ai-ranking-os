from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5


@dataclass(frozen=True)
class QueryScenario:
    id: str
    cluster: str
    intent: str
    text: str

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "cluster": self.cluster,
            "intent": self.intent,
            "text": self.text,
        }


class QueryMapBuilder:
    """Build a reproducible demand sample from user-supplied brand context."""

    VERSION = "1.0"

    def build(
        self,
        *,
        brand: str,
        language: str,
        region: str,
        profile: str,
        variables: dict[str, str],
    ) -> list[QueryScenario]:
        is_english = language.casefold().startswith("en")
        category = variables.get("category") or self._category(profile, english=is_english)
        audience = variables.get("audience") or ("customer" if is_english else "покупателя")
        product = variables.get("product") or (
            "the brand's products" if is_english else "продукты бренда"
        )
        if is_english:
            templates = [
                ("brand", "awareness", f"What is {brand} and what is it known for?"),
                ("category", "discovery", f"Which {category} brands are worth considering?"),
                (
                    "recommendation",
                    "recommendation",
                    f"What {category} would you recommend to a {audience}?",
                ),
                (
                    "problem",
                    "solution",
                    f"Which {category} products solve common customer problems?",
                ),
                ("comparison", "comparison", f"Compare {brand} with its strongest alternatives."),
                (
                    "trust",
                    "validation",
                    f"Is {brand} trustworthy? Use independent sources where possible.",
                ),
                (
                    "commercial",
                    "purchase",
                    f"Where and why should someone buy {product} from {brand}?",
                ),
                (
                    "evidence",
                    "research",
                    f"What independent publications or studies mention {brand}?",
                ),
            ]
        else:
            templates = [
                ("brand", "awareness", f"Что такое {brand} и чем известен этот бренд?"),
                (
                    "category",
                    "discovery",
                    f"Какие бренды в категории «{category}» стоит рассмотреть?",
                ),
                (
                    "recommendation",
                    "recommendation",
                    f"Что из категории «{category}» вы рекомендуете для {audience}?",
                ),
                (
                    "problem",
                    "solution",
                    f"Какие продукты категории «{category}» решают основные проблемы покупателей?",
                ),
                ("comparison", "comparison", f"Сравните {brand} с его сильнейшими альтернативами."),
                (
                    "trust",
                    "validation",
                    f"Можно ли доверять бренду {brand}? Приведите независимые источники.",
                ),
                ("commercial", "purchase", f"Где и почему стоит купить {product} бренда {brand}?"),
                (
                    "evidence",
                    "research",
                    f"Какие независимые публикации или исследования упоминают {brand}?",
                ),
            ]
        return [
            QueryScenario(
                id=str(uuid5(NAMESPACE_URL, f"ai-ranking-query:{brand}:{region}:{cluster}:{text}")),
                cluster=cluster,
                intent=intent,
                text=text,
            )
            for cluster, intent, text in templates
        ]

    @staticmethod
    def _category(profile: str, *, english: bool = False) -> str:
        if english:
            return {
                "BEAUTY": "beauty and skincare",
                "ECOMMERCE": "e-commerce products",
                "MEDICAL": "medical products and services",
                "GEO": "products and services",
                "ENTERPRISE": "enterprise solutions",
            }.get(profile, "products and services")
        return {
            "BEAUTY": "косметика и уход",
            "ECOMMERCE": "товары для электронной коммерции",
            "MEDICAL": "медицинские продукты и услуги",
            "GEO": "продукты и услуги",
            "ENTERPRISE": "корпоративные решения",
        }.get(profile, "продукты и услуги")


class ResearchPatternAnalyzer:
    VERSION = "1.0"

    def analyze(
        self,
        *,
        brand: str,
        responses: list[dict[str, Any]],
        entities: list[dict[str, Any]],
        citations: list[dict[str, Any]],
        query_catalog: list[dict[str, Any]],
    ) -> dict[str, Any]:
        target = brand.casefold().strip()
        entities_by_response: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
        citations_by_response: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
        for entity in entities:
            entities_by_response[entity["response_id"]].append(entity)
        for citation in citations:
            citations_by_response[citation["response_id"]].append(citation)
        catalog_by_text = {item["text"]: item for item in query_catalog}
        matrix = []
        competitor_counts: Counter[str] = Counter()
        source_counts: Counter[str] = Counter()
        for response in responses:
            response_entities = entities_by_response[response["id"]]
            mentioned = target in response["content"].casefold() or any(
                target in {item["name"].casefold(), item["canonical_name"].casefold()}
                for item in response_entities
            )
            competitors = sorted(
                {
                    item["canonical_name"]
                    for item in response_entities
                    if item["entity_type"] in {"BRAND", "PRODUCT", "ORGANIZATION"}
                    and item["canonical_name"].casefold() != target
                }
            )
            competitor_counts.update(competitors)
            sources = []
            for citation in citations_by_response[response["id"]]:
                source = (
                    urlparse(citation.get("url") or "").hostname
                    or citation.get("source")
                    or citation.get("title")
                )
                if source:
                    sources.append(source.casefold())
            source_counts.update(set(sources))
            scenario = catalog_by_text.get(response["prompt"], {})
            matrix.append(
                {
                    "response_id": response["id"],
                    "query_id": scenario.get("id"),
                    "cluster": scenario.get("cluster", "custom"),
                    "query": response["prompt"],
                    "provider": response["provider"],
                    "model": response["model"],
                    "mentioned": mentioned,
                    "competitors": competitors,
                    "sources": sorted(set(sources)),
                }
            )
        deficits = [item for item in matrix if not item["mentioned"]]
        return {
            "version": self.VERSION,
            "sample": {
                "queries": len(query_catalog),
                "responses": len(responses),
                "successful_responses": sum(not item.get("error_type") for item in responses),
                "providers": sorted({item["provider"] for item in responses}),
                "models": sorted({f"{item['provider']}/{item['model']}" for item in responses}),
            },
            "query_matrix": matrix,
            "deficit_queries": deficits,
            "competitors": [
                {"name": name, "response_count": count}
                for name, count in competitor_counts.most_common(10)
            ],
            "source_patterns": [
                {"resource": name, "response_count": count}
                for name, count in source_counts.most_common(15)
            ],
        }


class GeoOpportunityPlanner:
    VERSION = "1.0"

    def build(self, patterns: dict[str, Any]) -> list[dict[str, Any]]:
        deficits = patterns["deficit_queries"]
        sources = patterns["source_patterns"]
        competitors = patterns["competitors"]
        total = max(patterns["sample"]["responses"], 1)
        actions = []
        if sources:
            for source in sources[:5]:
                confidence = min(0.95, 0.45 + source["response_count"] / total)
                actions.append(
                    self._action(
                        channel="EARNED_MEDIA",
                        resource=source["resource"],
                        reason=(
                            f"Ресурс обнаружен в {source['response_count']} ответах "
                            "исследуемой выборки."
                        ),
                        deliverable=(
                            "Подготовить независимый экспертный материал с проверяемыми "
                            "фактами о бренде."
                        ),
                        metric="citation_score",
                        impact=(6, 18),
                        confidence=confidence,
                        effort="HIGH",
                        days=30,
                    )
                )
        else:
            actions.append(
                self._action(
                    channel="OWNED_MEDIA",
                    resource="Официальный сайт: раздел исследований, FAQ и источников",
                    reason="Ни одна модель не привела проверяемого внешнего источника о бренде.",
                    deliverable=(
                        "Опубликовать факты, методологию, авторов, даты, ссылки на "
                        "первичные данные и FAQ."
                    ),
                    metric="citation_score",
                    impact=(3, 12),
                    confidence=0.55,
                    effort="MEDIUM",
                    days=21,
                )
            )
            actions.append(
                self._action(
                    channel="INDUSTRY_MEDIA",
                    resource="Проверяемые отраслевые СМИ и экспертные площадки категории",
                    reason=(
                        "В выборке отсутствуют независимые подтверждения; конкретные "
                        "домены пока не выявлены."
                    ),
                    deliverable=(
                        "Получить редакционную публикацию, обзор или экспертный "
                        "комментарий с раскрытием источников."
                    ),
                    metric="citation_score",
                    impact=(5, 15),
                    confidence=0.4,
                    effort="HIGH",
                    days=45,
                )
            )
        if deficits:
            clusters = sorted({item["cluster"] for item in deficits})
            actions.append(
                self._action(
                    channel="CONTENT_GAP",
                    resource="Контент-хаб бренда",
                    reason=(
                        f"Бренд отсутствует в {len(deficits)} ответах; дефицитные "
                        f"кластеры: {', '.join(clusters)}."
                    ),
                    deliverable=(
                        "Создать отдельные доказательные материалы под каждый "
                        "дефицитный кластер запросов."
                    ),
                    metric="mention_score",
                    impact=(5, 20),
                    confidence=min(0.9, 0.5 + len(deficits) / total * 0.3),
                    effort="MEDIUM",
                    days=28,
                )
            )
        if competitors:
            leaders = ", ".join(item["name"] for item in competitors[:3])
            actions.append(
                self._action(
                    channel="COMPARISON",
                    resource="Независимые сравнения и страницы альтернатив",
                    reason=f"Вместо бренда модели регулярно называют: {leaders}.",
                    deliverable=(
                        "Подготовить проверяемое сравнение по критериям, где "
                        "преимущества подтверждены данными."
                    ),
                    metric="recommendation_score",
                    impact=(4, 14),
                    confidence=0.65,
                    effort="MEDIUM",
                    days=30,
                )
            )
        return sorted(
            actions,
            key=lambda item: (
                -(sum(item["expected_effect_range"]) / 2 * item["confidence"]),
                item["estimated_days"],
            ),
        )

    def _action(
        self,
        *,
        channel: str,
        resource: str,
        reason: str,
        deliverable: str,
        metric: str,
        impact: tuple[int, int],
        confidence: float,
        effort: str,
        days: int,
    ) -> dict[str, Any]:
        return {
            "id": str(uuid5(NAMESPACE_URL, f"geo-opportunity:{resource}:{metric}")),
            "version": self.VERSION,
            "channel": channel,
            "resource": resource,
            "reason": reason,
            "deliverable": deliverable,
            "affected_metric": metric,
            "expected_effect_range": list(impact),
            "confidence": round(confidence, 2),
            "effort": effort,
            "estimated_days": days,
            "verification": (
                "Повторить идентичную матрицу запросов после публикации и сравнить ответы."
            ),
            "causality_notice": (
                "Прогноз является гипотезой; рост подтверждается только повторным измерением."
            ),
        }
