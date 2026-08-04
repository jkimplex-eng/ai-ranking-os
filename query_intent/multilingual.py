import re

from query_intent.schemas import LanguageResult

LANGUAGE_MARKERS: dict[str, frozenset[str]] = {
    "ru": frozenset({"как", "что", "где", "купить", "лучший", "сравнить", "рядом"}),
    "es": frozenset({"cómo", "qué", "dónde", "comprar", "mejor", "comparar", "cerca"}),
    "fr": frozenset({"comment", "quoi", "où", "acheter", "meilleur", "comparer", "près"}),
    "de": frozenset({"wie", "was", "wo", "kaufen", "beste", "vergleichen", "nähe"}),
}


def detect_language(query: str) -> LanguageResult:
    lowered = query.casefold()
    tokens = set(re.findall(r"\w+", lowered, re.UNICODE))
    if re.search(r"[а-яё]", lowered):
        return LanguageResult(code="ru", confidence=0.99)

    scores = {
        language: len(tokens & markers)
        for language, markers in LANGUAGE_MARKERS.items()
        if language != "ru"
    }
    if scores and max(scores.values()) > 0:
        language = max(scores, key=scores.get)  # type: ignore[arg-type]
        return LanguageResult(code=language, confidence=min(0.95, 0.65 + scores[language] * 0.1))
    return LanguageResult(code="en", confidence=0.9)

