import re

from entity_extraction.schemas import ExtractedEntity, ResolutionLog


def normalize_name(name: str) -> str:
    return re.sub(r"[^\w]+", "", name.casefold())


def deduplicate(
    entities: list[ExtractedEntity],
) -> tuple[list[ExtractedEntity], dict[str, str], list[ResolutionLog]]:
    unique: dict[tuple[str, str], ExtractedEntity] = {}
    id_map: dict[str, str] = {}
    logs: list[ResolutionLog] = []
    for entity in entities:
        key = (normalize_name(entity.name), entity.entity_type)
        existing = unique.get(key)
        if existing is None:
            unique[key] = entity
            id_map[entity.temp_id] = entity.temp_id
            continue
        id_map[entity.temp_id] = existing.temp_id
        existing.confidence = max(existing.confidence, entity.confidence)
        existing.aliases = sorted(set(existing.aliases + entity.aliases + [entity.name]))
        logs.append(
            ResolutionLog(
                stage="deduplication",
                action="merge",
                details={"source_id": entity.temp_id, "target_id": existing.temp_id},
            )
        )
    return list(unique.values()), id_map, logs

