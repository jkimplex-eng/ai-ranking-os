import json
import re

from entity_extraction.entity_types import EntityType, parse_entity_type
from entity_extraction.schemas import ExtractedEntity

PATTERNS: tuple[tuple[EntityType, re.Pattern[str], float], ...] = (
    (EntityType.EMAIL, re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), 0.99),
    (EntityType.URL, re.compile(r"https?://[^\s<>()]+"), 0.99),
    (
        EntityType.MONEY,
        re.compile(r"(?:[$€£]\s?\d[\d,.]*|\d[\d,.]*\s?(?:USD|EUR|GBP|RUB|₽))", re.I),
        0.95,
    ),
    (EntityType.PERCENTAGE, re.compile(r"\b\d+(?:\.\d+)?\s?%"), 0.98),
    (
        EntityType.DATE,
        re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[./]\d{1,2}[./]\d{2,4})\b"),
        0.95,
    ),
    (EntityType.TIME, re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b"), 0.95),
    (
        EntityType.ORGANIZATION,
        re.compile(
            r"\b[A-ZА-Я][\w&.-]*(?:\s+[A-ZА-Я][\w&.-]*)*\s+"
            r"(?:Inc|Corp|Corporation|LLC|Ltd|Group|Company|АО|ООО)\b"
        ),
        0.9,
    ),
    (
        EntityType.PERSON,
        re.compile(r"\b[A-ZА-Я][a-zа-яё]+(?:\s+[A-ZА-Я][a-zа-яё]+){1,2}\b"),
        0.72,
    ),
)


def _parse_json_text(raw: str) -> object:
    stripped = raw.strip()
    if stripped.startswith(("{", "[")):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return raw
    return raw


def response_text(raw: object) -> str:
    if isinstance(raw, str):
        parsed = _parse_json_text(raw)
        if parsed is not raw:
            return response_text(parsed)
        return raw
    if isinstance(raw, dict):
        for key in ("text", "content", "response", "answer", "output"):
            if isinstance(raw.get(key), str):
                return raw[key]
        return json.dumps(raw, ensure_ascii=False, default=str)
    if isinstance(raw, list):
        return "\n".join(response_text(item) for item in raw)
    return str(raw)


def _structured_entities(raw: object) -> list[ExtractedEntity] | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("entities"), list):
        return None
    entities = []
    for index, item in enumerate(raw["entities"]):
        if isinstance(item, str):
            item = {"name": item}
        if not isinstance(item, dict):
            continue
        name = item.get("name", item.get("text", item.get("value")))
        if not name:
            continue
        entities.append(
            ExtractedEntity(
                temp_id=str(item.get("entity_id", item.get("id", f"e{index + 1}"))),
                name=str(name),
                entity_type=parse_entity_type(item.get("entity_type", item.get("type"))),
                confidence=float(item.get("confidence", 0.8)),
                start=item.get("start"),
                end=item.get("end"),
                aliases=[str(alias) for alias in item.get("aliases", [])],
                knowledge_graph_id=item.get(
                    "knowledge_graph_id",
                    item.get("kg_id"),
                ),
            )
        )
    return entities


def extract_entities(raw: object) -> tuple[str, list[ExtractedEntity]]:
    if isinstance(raw, str):
        parsed = _parse_json_text(raw)
        if parsed is not raw:
            raw = parsed
    text = response_text(raw)
    structured = _structured_entities(raw)
    if structured is not None:
        return text, structured

    entities: list[ExtractedEntity] = []
    occupied: list[tuple[int, int]] = []
    for entity_type, pattern, confidence in PATTERNS:
        for match in pattern.finditer(text):
            if any(match.start() < end and match.end() > start for start, end in occupied):
                continue
            entities.append(
                ExtractedEntity(
                    temp_id=f"e{len(entities) + 1}",
                    name=match.group().rstrip(".,;:"),
                    entity_type=entity_type,
                    confidence=confidence,
                    start=match.start(),
                    end=match.start() + len(match.group().rstrip(".,;:")),
                )
            )
            occupied.append((match.start(), match.end()))
    entities.sort(key=lambda item: (item.start if item.start is not None else -1, item.temp_id))
    return text, entities
