import hashlib
import math
import re

from query_intent.schemas import IntentType

DIMENSIONS = 128
PROTOTYPES: dict[IntentType, str] = {
    IntentType.INFORMATIONAL: "what who why explain definition facts information",
    IntentType.NAVIGATIONAL: "official website login page contact navigate",
    IntentType.TRANSACTIONAL: "buy purchase order book download register",
    IntentType.COMMERCIAL_INVESTIGATION: "price features reviews evaluate product",
    IntentType.COMPARISON: "compare versus alternative difference benchmark",
    IntentType.RECOMMENDATION: "best top recommend suggest ranking",
    IntentType.TROUBLESHOOTING: "error broken fix repair diagnose problem",
    IntentType.HOW_TO: "how instructions guide setup install configure tutorial",
    IntentType.LOCAL: "nearby near me local directions area",
    IntentType.RESEARCH: "research analysis evidence sources statistics report data",
}


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), re.UNICODE)


def embed(text: str) -> list[float]:
    vector = [0.0] * DIMENSIONS
    for token in _tokens(text):
        digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
        index = int.from_bytes(digest, "big") % DIMENSIONS
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


PROTOTYPE_VECTORS = {intent: embed(text) for intent, text in PROTOTYPES.items()}


def classify_with_embeddings(query: str) -> dict[IntentType, float]:
    query_vector = embed(query)
    return {
        intent: round(max(0.0, _cosine(query_vector, prototype)), 4)
        for intent, prototype in PROTOTYPE_VECTORS.items()
    }

