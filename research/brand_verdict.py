"""Conservative, versioned text evidence; not a claim of semantic model accuracy."""

import re
from dataclasses import asdict, dataclass

VERSION = "brand-verdict-1.0"


@dataclass(frozen=True)
class BrandVerdict:
    status: str
    evidence: tuple[str, ...]
    version: str = VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def classify_brand(content: str, brand: str) -> BrandVerdict:
    target = brand.strip()
    if not content.strip():
        return BrandVerdict("NOT_MEASURED", ())
    if not target:
        return BrandVerdict("NOT_MEASURED", ())
    name = rf"(?<!\w){re.escape(target)}(?!\w)"
    plain = re.sub(r"[*_`]+", "", content)
    segments = [s.strip() for s in re.split(r"[\n.!?;]+", plain) if s.strip()]
    evidence = [s for s in segments if re.search(name, s, re.I)]
    if not evidence:
        return BrandVerdict("NOT_MENTIONED", ())
    positive = negative = uncertain = False
    for sentence in evidence:
        # Split contrast clauses: a recommendation of B must not be attributed to A.
        clauses = re.split(r",\s*(?:но|а|but)\s+", sentence, flags=re.I)
        for clause in clauses:
            if not re.search(name, clause, re.I):
                continue
            negative_pattern = (
                r"(?:не\s+(?:рекомендую|рекомендуем|советую|советуем)|"
                rf"do\s+not\s+recommend|don't\s+recommend)\s+{name}"
            )
            positive_pattern = rf"(?:рекомендую|рекомендуем|советую|советуем|recommend)\s+{name}"
            reverse_pattern = rf"{name}\s+(?:рекомендую|рекомендуем|советую|советуем)\b"
            neg_reverse = rf"{name}\s+не\s+(?:рекомендую|рекомендуем|советую|советуем)\b"
            if re.search(negative_pattern, clause, re.I) or re.search(neg_reverse, clause, re.I):
                negative = True
            elif re.search(positive_pattern, clause, re.I) or re.search(
                reverse_pattern, clause, re.I
            ):
                if re.search(
                    r"\b(?:не|если|возможно|может|цитата|if|not|might)\b|[«»\"]", clause, re.I
                ):
                    uncertain = True
                else:
                    positive = True
            elif re.search(r"рекоменд|совету|recommend|suggest", clause, re.I):
                uncertain = True
    if uncertain or (positive and negative):
        status = "AMBIGUOUS"
    elif negative:
        status = "NOT_RECOMMENDED"
    elif positive:
        status = "RECOMMENDED"
    else:
        status = "MENTIONED"
    return BrandVerdict(status, tuple(evidence))
