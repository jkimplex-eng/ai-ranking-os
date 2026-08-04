from uuid import UUID, uuid5

from entity_extraction.deduplication import normalize_name
from entity_extraction.schemas import EntityResult, ExtractedEntity

KNOWLEDGE_NAMESPACE = UUID("d80a5e82-0439-4dc0-bf96-c9b737a36024")


def map_to_knowledge_graph(entities: list[ExtractedEntity]) -> list[EntityResult]:
    results = []
    for index, entity in enumerate(entities, start=1):
        canonical = entity.name.strip()
        kg_id = entity.knowledge_graph_id or (
            "kg:"
            + str(
                uuid5(
                    KNOWLEDGE_NAMESPACE,
                    f"{entity.entity_type}:{normalize_name(canonical)}",
                )
            )
        )
        results.append(
            EntityResult(
                entity_id=f"entity-{index}",
                name=entity.aliases[0] if entity.aliases else canonical,
                canonical_name=canonical,
                entity_type=entity.entity_type,
                confidence=round(entity.confidence, 4),
                aliases=sorted(set(entity.aliases)),
                knowledge_graph_id=kg_id,
            )
        )
    return results

