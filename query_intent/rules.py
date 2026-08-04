import re
from dataclasses import dataclass

from query_intent.schemas import INTENT_SUBTYPES, IntentType


@dataclass(frozen=True)
class RuleMatch:
    scores: dict[IntentType, float]
    subtypes: dict[IntentType, str]
    signals: dict[IntentType, list[str]]


RULES: dict[IntentType, tuple[tuple[str, str], ...]] = {
    IntentType.INFORMATIONAL: (
        (r"\b(?:what|who|when|why|что|кто|когда|почему|qué|quoi|was)\b", "FACTUAL"),
        (r"\b(?:define|meaning|definition|определение|значение)\b", "DEFINITION"),
        (r"\b(?:explain|объясни|объяснить)\b", "EXPLANATORY"),
    ),
    IntentType.NAVIGATIONAL: (
        (r"\b(?:official\s+site|website|сайт|sitio|site web)\b", "WEBSITE"),
        (r"\b(?:login|sign\s*in|войти|connexion)\b", "LOGIN"),
        (r"\b(?:contact|support page|контакты)\b", "CONTACT"),
    ),
    IntentType.TRANSACTIONAL: (
        (r"\b(?:buy|purchase|order|купить|заказать|comprar|acheter|kaufen)\b", "PURCHASE"),
        (r"\b(?:book|reserve|забронировать|réserver)\b", "BOOKING"),
        (r"\b(?:download|скачать|descargar|télécharger)\b", "DOWNLOAD"),
        (r"\b(?:sign\s*up|register|регистрация)\b", "SIGNUP"),
    ),
    IntentType.COMMERCIAL_INVESTIGATION: (
        (r"\b(?:price|pricing|cost|цена|стоимость|precio|prix|preis)\b", "PRICING"),
        (r"\b(?:features?|характеристики|fonctionnalités)\b", "FEATURES"),
        (r"\b(?:reviews?|отзывы|reseñas|avis|bewertungen)\b", "REVIEWS"),
    ),
    IntentType.COMPARISON: (
        (r"\b(?:vs|versus|compare|сравни|сравнить|comparar|comparer)\b", "VERSUS"),
        (r"\b(?:alternative|alternatives|аналоги|alternativa)\b", "ALTERNATIVES"),
        (r"\b(?:benchmark|бенчмарк)\b", "BENCHMARK"),
    ),
    IntentType.RECOMMENDATION: (
        (r"\b(?:best|top|лучший|лучшие|mejor|meilleur|beste)\b", "BEST_OF"),
        (r"\b(?:recommend|suggest|посоветуй|рекомендуй|recomendar)\b", "PERSONALIZED"),
        (r"\b(?:ranking|ranked|рейтинг)\b", "RANKED_LIST"),
    ),
    IntentType.TROUBLESHOOTING: (
        (r"\b(?:error|exception|ошибка|fehler|erreur)\b", "ERROR"),
        (r"\b(?:not working|doesn.t work|не работает|broken)\b", "DIAGNOSIS"),
        (r"\b(?:fix|repair|исправить|починить|réparer)\b", "REPAIR"),
    ),
    IntentType.HOW_TO: (
        (r"\b(?:how\s+to|как|cómo|comment|wie)\b", "INSTRUCTIONS"),
        (r"\b(?:setup|install|configure|настроить|установить)\b", "SETUP"),
        (r"\b(?:tutorial|guide|инструкция|руководство)\b", "TUTORIAL"),
    ),
    IntentType.LOCAL: (
        (r"\b(?:near\s+me|nearby|рядом|поблизости|cerca|près)\b", "NEARBY"),
        (r"\b(?:in\s+my\s+area|в моем городе|local service)\b", "LOCAL_SERVICE"),
        (r"\b(?:directions|route|маршрут|как добраться)\b", "DIRECTIONS"),
    ),
    IntentType.RESEARCH: (
        (r"\b(?:analy[sz]e|analysis|исследование|анализ)\b", "ANALYSIS"),
        (r"\b(?:evidence|sources|citations|источники|доказательства)\b", "EVIDENCE"),
        (r"\b(?:statistics|data|статистика|данные)\b", "STATISTICS"),
        (r"\b(?:report|отчет|отчёт|rapport)\b", "REPORT"),
    ),
}


def classify_with_rules(query: str) -> RuleMatch:
    scores = dict.fromkeys(IntentType, 0.0)
    subtypes = {intent: INTENT_SUBTYPES[intent][0] for intent in IntentType}
    signals: dict[IntentType, list[str]] = {intent: [] for intent in IntentType}
    for intent, patterns in RULES.items():
        for pattern, subtype in patterns:
            matches = re.findall(pattern, query, re.I)
            if not matches:
                continue
            scores[intent] += min(0.55, 0.3 + len(matches) * 0.1)
            subtypes[intent] = subtype
            signals[intent].append(pattern)
        scores[intent] = min(1.0, scores[intent])
    if re.match(r"\s*(?:compare|сравни(?:ть|те)?|comparar|comparer)\b", query, re.I):
        scores[IntentType.COMPARISON] = min(
            1.0,
            scores[IntentType.COMPARISON] + 0.2,
        )
        signals[IntentType.COMPARISON].append("leading_comparison_verb")
    if max(scores.values()) == 0:
        scores[IntentType.INFORMATIONAL] = 0.25
        subtypes[IntentType.INFORMATIONAL] = "EXPLANATORY"
        signals[IntentType.INFORMATIONAL].append("default")
    return RuleMatch(scores=scores, subtypes=subtypes, signals=signals)
