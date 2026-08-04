import re
import unicodedata
from difflib import SequenceMatcher

from entity_linking.ports import CanonicalRecord, EntityResolver, LinkableEntity, Resolution


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


class NameEntityResolver(EntityResolver):
    FUZZY_THRESHOLD = 0.80

    def resolve(self, entity: LinkableEntity, canonicals: list[CanonicalRecord]) -> Resolution:
        normalized = normalize_name(entity.canonical_name or entity.name)
        typed = [item for item in canonicals if item.entity_type == entity.entity_type]
        for canonical in typed:
            if canonical.normalized_name == normalized:
                return Resolution(canonical.id, 1.0, "EXACT_NAME")
        for canonical in typed:
            if normalized in canonical.aliases:
                return Resolution(canonical.id, 0.97, "EXACT_ALIAS")
        best_id = None
        best_score = 0.0
        for canonical in typed:
            names = (canonical.normalized_name, *canonical.aliases)
            score = max(SequenceMatcher(None, normalized, name).ratio() for name in names)
            if score > best_score:
                best_id, best_score = canonical.id, score
        if best_score >= self.FUZZY_THRESHOLD:
            return Resolution(best_id, round(best_score * 0.9, 4), "FUZZY_NAME")
        return Resolution(None, 1.0, "NEW_ENTITY")
