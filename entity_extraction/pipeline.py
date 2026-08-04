from datetime import UTC, datetime
from uuid import uuid4

from entity_extraction.alias_resolution import resolve_aliases
from entity_extraction.ambiguity import resolve_ambiguity
from entity_extraction.deduplication import deduplicate
from entity_extraction.extractor import extract_entities
from entity_extraction.knowledge_mapping import map_to_knowledge_graph
from entity_extraction.relations import extract_relations
from entity_extraction.schemas import (
    ExtractionInput,
    ExtractionResult,
    RelationResult,
    ResolutionLog,
)


def _compose_maps(first: dict[str, str], second: dict[str, str]) -> dict[str, str]:
    return {source: second.get(target, target) for source, target in first.items()}


def run_pipeline(
    payload: ExtractionInput,
    *,
    now: datetime | None = None,
) -> ExtractionResult:
    text, extracted = extract_entities(payload.raw_response)
    relations = extract_relations(payload.raw_response, text, extracted)

    deduplicated, dedup_map, dedup_logs = deduplicate(extracted)
    resolved, alias_map, alias_logs = resolve_aliases(deduplicated)
    resolved, ambiguity_logs = resolve_ambiguity(resolved)
    final_entities = map_to_knowledge_graph(resolved)

    temp_to_final = {
        entity.temp_id: final.entity_id
        for entity, final in zip(resolved, final_entities, strict=True)
    }
    source_to_resolved = _compose_maps(dedup_map, alias_map)
    final_relations: list[RelationResult] = []
    seen_relations: set[tuple[str, str, str]] = set()
    relation_logs: list[ResolutionLog] = []
    for relation in relations:
        source_temp = source_to_resolved.get(relation.source_entity_id, relation.source_entity_id)
        target_temp = source_to_resolved.get(relation.target_entity_id, relation.target_entity_id)
        source_id = temp_to_final.get(source_temp)
        target_id = temp_to_final.get(target_temp)
        if source_id is None or target_id is None or source_id == target_id:
            relation_logs.append(
                ResolutionLog(
                    stage="relation_resolution",
                    action="drop_unresolved",
                    details={"relation_id": relation.relation_id},
                )
            )
            continue
        key = (source_id, target_id, str(relation.relation_type))
        if key in seen_relations:
            continue
        seen_relations.add(key)
        final_relations.append(
            RelationResult(
                relation_id=f"relation-{len(final_relations) + 1}",
                source_entity_id=source_id,
                target_entity_id=target_id,
                relation_type=str(relation.relation_type),
                confidence=round(relation.confidence, 4),
            )
        )

    return ExtractionResult(
        response_id=payload.response_id or str(uuid4()),
        entities=final_entities,
        relations=final_relations,
        resolution_logs=dedup_logs + alias_logs + ambiguity_logs + relation_logs,
        processed_at=now or datetime.now(UTC),
    )

