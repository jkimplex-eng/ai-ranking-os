import re
from enum import StrEnum

from entity_extraction.schemas import ExtractedEntity, ExtractedRelation


class RelationType(StrEnum):
    AFFILIATED_WITH = "AFFILIATED_WITH"
    WORKS_FOR = "WORKS_FOR"
    FOUNDED_BY = "FOUNDED_BY"
    OWNS = "OWNS"
    SUBSIDIARY_OF = "SUBSIDIARY_OF"
    PART_OF = "PART_OF"
    LOCATED_IN = "LOCATED_IN"
    HEADQUARTERED_IN = "HEADQUARTERED_IN"
    CREATED_BY = "CREATED_BY"
    DEVELOPED_BY = "DEVELOPED_BY"
    MANUFACTURED_BY = "MANUFACTURED_BY"
    COMPETES_WITH = "COMPETES_WITH"
    PARTNERS_WITH = "PARTNERS_WITH"
    ACQUIRED = "ACQUIRED"
    INVESTED_IN = "INVESTED_IN"
    USES = "USES"
    PRODUCES = "PRODUCES"
    OFFERS = "OFFERS"
    RECOMMENDS = "RECOMMENDS"
    MENTIONS = "MENTIONS"
    CITES = "CITES"
    LINKS_TO = "LINKS_TO"
    OCCURRED_ON = "OCCURRED_ON"
    HAS_PRICE = "HAS_PRICE"
    HAS_ATTRIBUTE = "HAS_ATTRIBUTE"
    ALIAS_OF = "ALIAS_OF"
    RELATED_TO = "RELATED_TO"


RELATION_PHRASES: tuple[tuple[re.Pattern[str], RelationType], ...] = (
    (re.compile(r"\bworks?\s+for\b", re.I), RelationType.WORKS_FOR),
    (re.compile(r"\bfounded\s+by\b", re.I), RelationType.FOUNDED_BY),
    (re.compile(r"\bacquired\b", re.I), RelationType.ACQUIRED),
    (re.compile(r"\bowns?\b", re.I), RelationType.OWNS),
    (re.compile(r"\bpartners?\s+with\b", re.I), RelationType.PARTNERS_WITH),
    (re.compile(r"\bcompetes?\s+with\b", re.I), RelationType.COMPETES_WITH),
    (re.compile(r"\buses?\b", re.I), RelationType.USES),
    (re.compile(r"\bproduces?\b", re.I), RelationType.PRODUCES),
    (re.compile(r"\brecommends?\b", re.I), RelationType.RECOMMENDS),
    (re.compile(r"\blocated\s+in\b", re.I), RelationType.LOCATED_IN),
)


def parse_relation_type(value: object) -> RelationType:
    normalized = str(value or "RELATED_TO").upper().replace(" ", "_")
    try:
        return RelationType(normalized)
    except ValueError:
        return RelationType.RELATED_TO


def extract_relations(
    raw: object,
    text: str,
    entities: list[ExtractedEntity],
) -> list[ExtractedRelation]:
    if isinstance(raw, dict) and isinstance(raw.get("relations"), list):
        relations: list[ExtractedRelation] = []
        for index, item in enumerate(raw["relations"]):
            if not isinstance(item, dict):
                continue
            source = item.get("source_entity_id", item.get("source", item.get("from")))
            target = item.get("target_entity_id", item.get("target", item.get("to")))
            if source is None or target is None:
                continue
            relations.append(
                ExtractedRelation(
                    relation_id=str(item.get("relation_id", item.get("id", f"r{index + 1}"))),
                    source_entity_id=str(source),
                    target_entity_id=str(target),
                    relation_type=parse_relation_type(
                        item.get("relation_type", item.get("type", item.get("relation")))
                    ),
                    confidence=float(item.get("confidence", 0.8)),
                )
            )
        return relations

    relations = []
    positioned = [
        entity
        for entity in entities
        if entity.start is not None and entity.end is not None
    ]
    for source in positioned:
        for target in positioned:
            if source.temp_id == target.temp_id or source.end is None or target.start is None:
                continue
            if source.end >= target.start:
                continue
            between = text[source.end : target.start]
            if len(between) > 80 or any(mark in between for mark in ".!?\n"):
                continue
            for pattern, relation_type in RELATION_PHRASES:
                if pattern.search(between):
                    relations.append(
                        ExtractedRelation(
                            relation_id=f"r{len(relations) + 1}",
                            source_entity_id=source.temp_id,
                            target_entity_id=target.temp_id,
                            relation_type=relation_type,
                            confidence=0.75,
                        )
                    )
                    break
    return relations
