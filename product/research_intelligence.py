from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5

from product.geography import query_context


@dataclass(frozen=True)
class QueryScenario:
    id: str
    cluster: str
    intent: str
    text: str
    buyer_stage: str = "consideration"
    brand_mode: str = "unbranded"
    rationale: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "cluster": self.cluster,
            "intent": self.intent,
            "text": self.text,
            "buyer_stage": self.buyer_stage,
            "brand_mode": self.brand_mode,
            "rationale": self.rationale,
        }


class QueryMapBuilder:
    """Build natural buyer questions from verified brand and product context."""

    VERSION = "2.1"
    CURATED_QUERY_SETS: dict[str, tuple[tuple[str, str], ...]] = {
        "skillbox": (
            ("design", "Где учиться дизайну с нуля онлайн?"),
            ("design", "Какой курс графического дизайна выбрать для смены профессии?"),
            ("design", "Посоветуй обучение UX/UI-дизайну с практикой и портфолио."),
            ("design", "Какую онлайн-школу дизайна выбрать работающему человеку?"),
            ("design", "Где учиться дизайну, чтобы искать работу в Москве?"),
            ("generative_ai", "Где научиться пользоваться нейросетями для работы с нуля?"),
            (
                "generative_ai",
                "Какой практический курс по генеративному ИИ выбрать маркетологу?",
            ),
            (
                "generative_ai",
                "Посоветуй обучение нейросетям для создания текста, изображений и видео.",
            ),
            (
                "generative_ai",
                "Какой онлайн-курс по ИИ подойдёт без технического образования?",
            ),
            ("generative_ai", "Где в России учиться применению нейросетей в бизнесе?"),
            ("programming", "Какую онлайн-школу программирования выбрать новичку?"),
            ("programming", "Где учиться Python с нуля для смены профессии?"),
            ("programming", "Какой курс веб-разработки выбрать работающему человеку?"),
            (
                "programming",
                "Посоветуй обучение программированию с проектами и карьерной поддержкой.",
            ),
            ("programming", "Где учиться разработке, чтобы искать первую работу в Москве?"),
            ("marketing", "Где учиться интернет-маркетингу с нуля?"),
            ("marketing", "Какой онлайн-курс выбрать для перехода в digital-маркетинг?"),
            (
                "marketing",
                "Посоветуй обучение performance-маркетингу с практическими заданиями.",
            ),
            ("marketing", "Какую школу выбрать для изучения SMM, рекламы и аналитики?"),
            ("marketing", "Где учиться маркетингу для работы с российскими компаниями?"),
        ),
    }

    def build(
        self,
        *,
        brand: str,
        language: str,
        region: str,
        profile: str,
        variables: dict[str, str],
        brand_profile: dict[str, Any] | None = None,
        competitor_profiles: list[dict[str, Any]] | None = None,
    ) -> list[QueryScenario]:
        is_english = language.casefold().startswith("en")
        curated = self.CURATED_QUERY_SETS.get(brand.casefold().strip())
        if curated and not is_english:
            return [
                QueryScenario(
                    id=str(
                        uuid5(
                            NAMESPACE_URL,
                            f"ai-ranking-query:{brand}:{region}:{cluster}:{text}",
                        )
                    ),
                    cluster=cluster,
                    intent="recommendation",
                    text=text,
                    buyer_stage="consideration",
                    brand_mode="unbranded",
                    rationale="Проверяет естественный покупательский спрос в направлении обучения.",
                )
                for cluster, text in curated
            ]
        profile_data = brand_profile or {}
        detected_categories = [
            str(item).strip() for item in profile_data.get("categories", []) if item
        ]
        attributes = [str(item).strip() for item in profile_data.get("attributes", []) if item]
        fallback_category = (
            variables.get("category")
            or next(iter(detected_categories), None)
            or self._category(profile, english=is_english)
        )
        categories = list(dict.fromkeys(detected_categories or [fallback_category]))[:4]
        products = [item for item in profile_data.get("products", []) if item.get("name")]
        price_context = self._price_context(products, english=is_english)
        competitors = list(
            dict.fromkeys(
                str(item.get("brand") or item.get("name") or "").strip()
                for item in (competitor_profiles or [])
                if item.get("brand") or item.get("name")
            )
        )
        if is_english:
            needs = list(
                dict.fromkeys([*attributes, *self._default_needs(profile, True, fallback_category)])
            )[:4]
            terms = [self._product_term(item, True) for item in categories]
            templates = [
                (
                    "category_discovery",
                    "recommendation",
                    self._discovery_question(term, need, index, True),
                    "discovery",
                    "unbranded",
                )
                for index, (term, need) in enumerate(
                    zip((terms * 7)[:7], (needs * 7)[:7], strict=False)
                )
            ]
            templates += [
                (
                    "problem_solution",
                    "solution",
                    f"Which {fallback_category} options work best for {need}?",
                    "consideration",
                    "unbranded",
                )
                for need in needs[:3]
            ]
            templates += [
                (
                    "price_comparison",
                    "comparison",
                    (
                        f"Which options in {term} for {needs[index % len(needs)]} offer "
                        f"the best value, features, and verified outcomes {price_context}?"
                    ),
                    "consideration",
                    "unbranded",
                )
                for index, term in enumerate((terms * 2)[:2])
            ]
            templates += [
                (
                    "trust_evidence",
                    "validation",
                    (
                        f"Which {fallback_category} brands publish credible product research "
                        "and independent evidence?"
                    ),
                    "validation",
                    "unbranded",
                ),
                (
                    "trust_evidence",
                    "validation",
                    f"Which {fallback_category} brands are trusted by experts and why?",
                    "validation",
                    "unbranded",
                ),
            ]
            templates += self._competitor_questions(
                brand=brand,
                competitors=competitors,
                category=fallback_category,
                need=needs[0],
                price_context=price_context,
                english=True,
            )
            templates += [
                (
                    "brand_control",
                    "brand",
                    f"Is {brand} worth considering and for whom?",
                    "validation",
                    "branded",
                ),
                (
                    "brand_control",
                    "comparison",
                    (
                        f"What are the strongest alternatives to {brand} at a similar price "
                        "and with similar features?"
                    ),
                    "consideration",
                    "branded",
                ),
            ]
        else:
            needs = [
                self._need_context(item)
                for item in dict.fromkeys(
                    [*attributes, *self._default_needs(profile, False, fallback_category)]
                )
            ][:4]
            terms = [self._product_term(item, False) for item in categories]
            templates = [
                (
                    "category_discovery",
                    "recommendation",
                    self._discovery_question(term, need, index, False),
                    "discovery",
                    "unbranded",
                )
                for index, (term, need) in enumerate(
                    zip((terms * 7)[:7], (needs * 7)[:7], strict=False)
                )
            ]
            templates += [
                (
                    "problem_solution",
                    "solution",
                    f"Какие варианты в категории «{fallback_category}» подходят для {need}?",
                    "consideration",
                    "unbranded",
                )
                for need in needs[:3]
            ]
            templates += [
                (
                    "price_comparison",
                    "comparison",
                    (
                        f"Какие предложения в категории «{self._comparison_term(term)}» для "
                        f"{needs[index % len(needs)]} лучше по цене, характеристикам и "
                        f"подтверждённым результатам {price_context}?"
                    ),
                    "consideration",
                    "unbranded",
                )
                for index, term in enumerate((terms * 2)[:2])
            ]
            templates += [
                (
                    "trust_evidence",
                    "validation",
                    (
                        f"Какие бренды в категории «{fallback_category}» публикуют "
                        "достоверные исследования и независимые подтверждения?"
                    ),
                    "validation",
                    "unbranded",
                ),
                (
                    "trust_evidence",
                    "validation",
                    f"Каким брендам в категории «{fallback_category}» доверяют эксперты и почему?",
                    "validation",
                    "unbranded",
                ),
            ]
            templates += self._competitor_questions(
                brand=brand,
                competitors=competitors,
                category=fallback_category,
                need=needs[0],
                price_context=price_context,
                english=False,
            )
            templates += [
                (
                    "brand_control",
                    "brand",
                    f"Стоит ли рассматривать {brand} и кому подходит этот бренд?",
                    "validation",
                    "branded",
                ),
                (
                    "brand_control",
                    "comparison",
                    f"Какие альтернативы {brand} сопоставимы по цене и характеристикам?",
                    "consideration",
                    "branded",
                ),
            ]
        templates = self._deduplicate(templates)
        location = query_context(region, english=is_english)
        if location:
            templates = [
                (cluster, intent, self._with_location(text, location), buyer_stage, brand_mode)
                for cluster, intent, text, buyer_stage, brand_mode in templates
            ]
        return [
            QueryScenario(
                id=str(uuid5(NAMESPACE_URL, f"ai-ranking-query:{brand}:{region}:{cluster}:{text}")),
                cluster=cluster,
                intent=intent,
                text=text,
                buyer_stage=buyer_stage,
                brand_mode=brand_mode,
                rationale=self._rationale(cluster, english=is_english),
            )
            for cluster, intent, text, buyer_stage, brand_mode in templates
        ]

    @staticmethod
    def _with_location(text: str, location: str) -> str:
        """Add geography to a natural question without changing its intent."""

        stripped = text.rstrip()
        if not stripped:
            return stripped
        natural_text = f"{stripped[0].lower()}{stripped[1:]}"
        natural_location = f"{location[0].upper()}{location[1:]}"
        return f"{natural_location}, {natural_text}"

    @staticmethod
    def _price_context(products: list[dict[str, Any]], *, english: bool) -> str:
        prices: list[float] = []
        currency = ""
        for product in products:
            try:
                prices.append(float(str(product.get("price") or "").replace(" ", "")))
                currency = str(product.get("currency") or currency)
            except ValueError:
                continue
        if not prices:
            return "in the mid-price segment" if english else "в среднем ценовом сегменте"
        ceiling = int(max(prices) * 1.15 // 100 * 100 + 100)
        if english:
            return f"under {ceiling} {currency or 'in local currency'}"
        unit = "рублей" if currency.casefold() in {"rub", "руб", "₽"} else currency
        return f"до {ceiling} {unit or 'в местной валюте'}"

    @staticmethod
    def _competitor_questions(
        *,
        brand: str,
        competitors: list[str],
        category: str,
        need: str,
        price_context: str,
        english: bool,
    ) -> list[tuple[str, str, str, str, str]]:
        if english:
            first = competitors[0] if competitors else f"leading {category} brands"
            second = competitors[1] if len(competitors) > 1 else f"popular {category} brands"
            alternative = (
                f"What alternatives to {first} have similar features {price_context}?"
                if competitors
                else f"Which {category} brands have similar features {price_context}?"
            )
            replacement = (
                f"What should I choose instead of {second} for {need}?"
                if competitors
                else f"Which {category} brands should I choose for {need}?"
            )
            return [
                (
                    "competitor_alternative",
                    "comparison",
                    alternative,
                    "consideration",
                    "comparative",
                ),
                (
                    "competitor_alternative",
                    "replacement",
                    replacement,
                    "consideration",
                    "comparative",
                ),
                (
                    "competitor_comparison",
                    "comparison",
                    f"Compare {brand} with {first} by price, features, and evidence.",
                    "validation",
                    "comparative",
                ),
                (
                    "competitor_comparison",
                    "comparison",
                    f"Which {category} brands outperform {brand}, and on which criteria?",
                    "validation",
                    "comparative",
                ),
            ]
        first = competitors[0] if competitors else f"ведущие бренды категории «{category}»"
        second = (
            competitors[1] if len(competitors) > 1 else f"популярные бренды категории «{category}»"
        )
        alternative = (
            f"Какие альтернативы {first} имеют похожие характеристики {price_context}?"
            if competitors
            else (
                f"Какие бренды категории «{category}» имеют похожие характеристики {price_context}?"
            )
        )
        replacement = (
            f"Что выбрать вместо {second} для {need}?"
            if competitors
            else f"Какие бренды категории «{category}» выбрать для {need}?"
        )
        return [
            (
                "competitor_alternative",
                "comparison",
                alternative,
                "consideration",
                "comparative",
            ),
            (
                "competitor_alternative",
                "replacement",
                replacement,
                "consideration",
                "comparative",
            ),
            (
                "competitor_comparison",
                "comparison",
                f"Сравните {brand} и {first} по цене, характеристикам и доказательствам.",
                "validation",
                "comparative",
            ),
            (
                "competitor_comparison",
                "comparison",
                f"Какие бренды категории «{category}» превосходят {brand} и по каким критериям?",
                "validation",
                "comparative",
            ),
        ]

    @staticmethod
    def _rationale(cluster: str, *, english: bool) -> str:
        labels = {
            "category_discovery": "Checks spontaneous recommendation for a concrete need.",
            "problem_solution": "Checks whether the brand appears when the buyer states a problem.",
            "price_comparison": "Checks price and feature competitiveness.",
            "trust_evidence": "Checks independent authority and evidence signals.",
            "competitor_alternative": "Checks whether the brand appears as an alternative.",
            "competitor_comparison": "Checks strengths and weaknesses against competitors.",
            "brand_control": "Control query measuring direct brand knowledge.",
        }
        if english:
            return labels.get(cluster, "Checks buyer demand.")
        return {
            "category_discovery": "Проверяет естественную рекомендацию под конкретную потребность.",
            "problem_solution": "Проверяет появление бренда при описании проблемы покупателя.",
            "price_comparison": "Проверяет конкурентоспособность по цене и характеристикам.",
            "trust_evidence": "Проверяет независимые источники и сигналы доверия.",
            "competitor_alternative": "Проверяет появление бренда среди альтернатив конкуренту.",
            "competitor_comparison": "Проверяет сильные и слабые стороны относительно конкурентов.",
            "brand_control": "Контрольный запрос на прямое знание бренда.",
        }.get(cluster, "Проверяет покупательский спрос.")

    @staticmethod
    def _deduplicate(
        items: list[tuple[str, str, str, str, str]],
    ) -> list[tuple[str, str, str, str, str]]:
        result = []
        seen: set[str] = set()
        for item in items:
            key = re.sub(r"\W+", " ", item[2].casefold()).strip()
            if key not in seen and 12 <= len(item[2]) <= 500:
                seen.add(key)
                result.append(item)
        return result

    @staticmethod
    def _product_term(category: str, english: bool) -> str:
        if english:
            return category.casefold()
        known = {
            "сыворотки": "сыворотку",
            "кремы": "крем",
            "тонеры": "тонер",
            "маски": "маску",
            "средства очищения": "средство для очищения",
            "spf-защита": "SPF-крем",
        }
        return known.get(category.casefold(), category.casefold())

    @staticmethod
    def _recommendation_question(term: str, need: str) -> str:
        if term in {"сыворотку", "маску"}:
            return f"Какую {term} вы бы порекомендовали для {need}?"
        if term.startswith("средство"):
            return f"Какое {term} вы бы порекомендовали для {need}?"
        if term in {"крем", "тонер", "SPF-крем"}:
            return f"Какой {term} вы бы порекомендовали для {need}?"
        return f"Что из категории «{term}» вы бы порекомендовали для {need}?"

    @staticmethod
    def _comparison_term(term: str) -> str:
        return {
            "сыворотку": "сыворотки",
            "маску": "маски",
            "крем": "кремы",
            "тонер": "тонеры",
            "SPF-крем": "SPF-кремы",
            "средство для очищения": "средства для очищения",
        }.get(term, term)

    @staticmethod
    def _need_context(value: str) -> str:
        normalized = value.casefold().strip()
        known = {
            "чувствительная кожа": "чувствительной кожи",
            "ниацинамид": "ухода с ниацинамидом",
            "витамин c": "ухода с витамином C",
            "гиалуроновая кислота": "увлажнения с гиалуроновой кислотой",
            "увлажняющий": "интенсивного увлажнения",
            "увлажнение чувствительной кожи": "увлажнения чувствительной кожи",
            "пигментация и постакне": "пигментации и постакне",
            "первые возрастные изменения": "первых возрастных изменений",
            "покраснение и нарушенный защитный барьер": (
                "покраснения и восстановления защитного барьера"
            ),
            "обучение с нуля": "обучения с нуля",
            "освоение новой профессии": "освоения новой профессии",
            "помощь с трудоустройством": "обучения с помощью в трудоустройстве",
            "гибкий график обучения": "обучения по гибкому графику",
            "практические проекты": "обучения с практическими проектами",
        }
        return known.get(normalized, value.strip())

    @classmethod
    def _discovery_question(cls, term: str, need: str, index: int, english: bool) -> str:
        if english:
            variants = (
                f"Which {term} would you recommend for {need}?",
                f"What are the best {term} for {need}?",
                f"Which {term} offers the best value for {need}?",
            )
            return variants[(index // 4) % len(variants)]
        base = cls._recommendation_question(term, need)
        variants = (
            base,
            base.replace("вы бы порекомендовали", "лучше выбрать"),
            base.replace("вы бы порекомендовали", "даёт лучшее соотношение цены и результата"),
        )
        return variants[(index // 4) % len(variants)]

    @staticmethod
    def _default_needs(profile: str, english: bool, category: str = "") -> list[str]:
        normalized_category = category.casefold()
        if "образован" in normalized_category or "education" in normalized_category:
            return (
                [
                    "starting a new career without prior experience",
                    "job-ready practical skills",
                    "a flexible learning schedule",
                    "career support and a strong portfolio",
                ]
                if english
                else [
                    "освоения новой профессии с нуля",
                    "получения практических навыков для работы",
                    "обучения по гибкому графику",
                    "подготовки портфолио и трудоустройства",
                ]
            )
        if profile == "BEAUTY":
            return (
                [
                    "sensitive dehydrated skin",
                    "pigmentation and post-acne marks",
                    "first signs of aging",
                    "redness and a damaged skin barrier",
                ]
                if english
                else [
                    "увлажнение чувствительной кожи",
                    "пигментация и постакне",
                    "первые возрастные изменения",
                    "покраснение и нарушенный защитный барьер",
                ]
            )
        return (
            ["best value", "reliable quality", "expert recommendation", "a proven solution"]
            if english
            else [
                "лучшее соотношение цены и качества",
                "надёжное качество",
                "рекомендация экспертов",
                "доказанная эффективность",
            ]
        )

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
        manual_competitors: list[dict[str, Any]] | None = None,
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
            "competitors": self._competitors(competitor_counts, manual_competitors or []),
            "source_patterns": [
                {"resource": name, "response_count": count}
                for name, count in source_counts.most_common(15)
            ],
        }

    @staticmethod
    def _competitors(observed: Counter[str], manual: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for item in manual:
            name = str(item.get("name") or "").strip()
            if name:
                merged[name.casefold()] = {
                    "name": name,
                    "response_count": observed.get(name, 0),
                    "origin": "MANUAL",
                    "website_url": item.get("website_url"),
                }
        for name, count in observed.most_common(10):
            key = name.casefold()
            if key in merged:
                merged[key]["response_count"] = count
                merged[key]["origin"] = "MANUAL_AND_OBSERVED"
            else:
                merged[key] = {
                    "name": name,
                    "response_count": count,
                    "origin": "OBSERVED",
                    "website_url": None,
                }
        return sorted(
            merged.values(), key=lambda item: (-item["response_count"], item["name"].casefold())
        )


class CompetitiveInfluenceEngine:
    """Compare like-for-like products and observed publication evidence."""

    VERSION = "1.0"

    def compare(
        self,
        *,
        target_profile: dict[str, Any],
        competitor_profiles: list[dict[str, Any]],
        patterns: dict[str, Any],
    ) -> dict[str, Any]:
        comparisons = []
        for competitor in competitor_profiles:
            matches = self._product_matches(target_profile, competitor)
            observed = next(
                (
                    item
                    for item in patterns["competitors"]
                    if item["name"].casefold() == competitor["brand"].casefold()
                ),
                None,
            )
            comparisons.append(
                {
                    "competitor": competitor["brand"],
                    "website_url": competitor["website_url"],
                    "response_count": observed["response_count"] if observed else 0,
                    "matched_products": matches,
                    "evidence_urls": competitor.get("evidence_urls", []),
                    "profile_confidence": competitor.get("confidence", 0),
                }
            )
        source_influence = [
            {
                **source,
                "relationship": "OBSERVED_ASSOCIATION",
                "explanation": (
                    "Домен присутствует в ответах исследуемой выборки. Это корреляция, "
                    "а не доказанная причина более высокой видимости."
                ),
            }
            for source in patterns["source_patterns"]
        ]
        return {
            "version": self.VERSION,
            "competitors": comparisons,
            "source_influence": source_influence,
            "causality_status": "NOT_ESTABLISHED",
            "verification": (
                "Для проверки влияния нужна публикация, контрольная группа запросов и "
                "повторное исследование с неизменной матрицей."
            ),
        }

    @staticmethod
    def _product_matches(
        target: dict[str, Any], competitor: dict[str, Any]
    ) -> list[dict[str, Any]]:
        matches = []
        for own in target.get("products", []):
            own_terms = CompetitiveInfluenceEngine._terms(own)
            best: tuple[float, dict[str, Any]] | None = None
            for rival in competitor.get("products", []):
                rival_terms = CompetitiveInfluenceEngine._terms(rival)
                union = own_terms | rival_terms
                similarity = len(own_terms & rival_terms) / len(union) if union else 0.0
                if best is None or similarity > best[0]:
                    best = (similarity, rival)
            if best and best[0] > 0:
                matches.append(
                    {
                        "target_product": own["name"],
                        "competitor_product": best[1]["name"],
                        "feature_similarity": round(best[0], 3),
                        "target_price": own.get("price"),
                        "competitor_price": best[1].get("price"),
                        "currency": own.get("currency") or best[1].get("currency"),
                        "target_evidence_url": own.get("evidence_url"),
                        "competitor_evidence_url": best[1].get("evidence_url"),
                    }
                )
        return matches

    @staticmethod
    def _terms(product: dict[str, Any]) -> set[str]:
        value = " ".join(
            str(product.get(key) or "") for key in ("name", "category", "description")
        ).casefold()
        return {token for token in re.findall(r"[\w-]{4,}", value) if token}


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
        baseline_actions = [
            (
                "ENTITY",
                "Официальный сайт: карточка компании и структурированные данные",
                (
                    "ИИ должен однозначно связать название компании, официальный домен, "
                    "услуги и регион."
                ),
                (
                    "Добавить Organization/Brand JSON-LD, реквизиты, контакты, "
                    "canonical URL и единое описание компании."
                ),
                "mention_score",
                (2, 8),
                0.45,
                "LOW",
                14,
            ),
            (
                "DEMAND_CONTENT",
                "Официальный сайт: ответы на частотные вопросы Wordstat",
                f"Проверено {len(deficits)} запросов с дефицитом присутствия бренда.",
                (
                    "Для приоритетных запросов создать самостоятельные страницы "
                    "с прямым ответом, фактами и датой обновления."
                ),
                "coverage_score",
                (3, 12),
                0.5,
                "MEDIUM",
                21,
            ),
            (
                "FAQ",
                "Официальный сайт: FAQ покупателей",
                (
                    "Структурированные ответы помогают извлечь условия выбора, "
                    "ограничения и отличия продукта."
                ),
                (
                    "Собрать FAQ из выбранных запросов, дать короткий ответ и "
                    "развернутое доказательство, добавить FAQPage-разметку."
                ),
                "coverage_score",
                (2, 9),
                0.4,
                "LOW",
                14,
            ),
            (
                "EVIDENCE",
                "Официальный сайт: авторы, методология и первичные доказательства",
                (
                    "Рекомендации без проверяемого автора, даты и первичного "
                    "источника слабее подтверждаются."
                ),
                (
                    "Указать экспертов и редакционную политику; каждое числовое "
                    "утверждение связать с первичным источником."
                ),
                "citation_score",
                (3, 10),
                0.5,
                "MEDIUM",
                21,
            ),
            (
                "SOURCE_MONITORING",
                "Мониторинг источников Алисы и конкурентов",
                (
                    f"В текущей выборке найдено {len(sources)} повторяющихся источников "
                    f"и {len(competitors)} конкурентов."
                ),
                (
                    "Ежедневно или еженедельно сохранять названные URL, домены, "
                    "конкурентов и позиции по неизменному набору вопросов."
                ),
                "citation_score",
                (0, 8),
                0.55,
                "LOW",
                30,
            ),
            (
                "VERIFICATION",
                "Контрольное повторное исследование",
                (
                    "Наблюдаемая связь не доказывает, что отдельная публикация "
                    "стала причиной изменения рекомендации."
                ),
                (
                    "Зафиксировать действие и URL, затем повторить тот же набор "
                    "запросов и сравнить с контрольной группой."
                ),
                "confidence_score",
                (0, 10),
                0.75,
                "LOW",
                30,
            ),
        ]
        existing_resources = {item["resource"] for item in actions}
        for (
            channel,
            resource,
            reason,
            deliverable,
            metric,
            impact,
            confidence,
            effort,
            days,
        ) in baseline_actions:
            if resource in existing_resources:
                continue
            actions.append(
                self._action(
                    channel=channel,
                    resource=resource,
                    reason=reason,
                    deliverable=deliverable,
                    metric=metric,
                    impact=impact,
                    confidence=confidence,
                    effort=effort,
                    days=days,
                )
            )
        return sorted(
            actions,
            key=lambda item: (
                -(sum(item["expected_effect_range"]) / 2 * item["confidence"]),
                item["estimated_days"],
            ),
        )[:10]

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
