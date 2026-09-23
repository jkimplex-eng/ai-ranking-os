"""Conservative, versioned text evidence; not a claim of semantic model accuracy."""

import re
from dataclasses import asdict, dataclass

VERSION = "brand-verdict-1.2"


@dataclass(frozen=True)
class BrandVerdict:
    status: str
    evidence: tuple[str, ...]
    version: str = VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def _proposed_as_option(content: str, name: str) -> bool:
    """Detect an offered choice only when the answer supplies choice context."""
    direct = rf"\b(?:можно|стоит)\s+(?:рассмотреть|сравнить|выбрать)\s+{name}"
    if re.search(direct, re.sub(r"[*_`]+", "", content), re.I):
        return True
    lines = content.splitlines()
    listed = [
        index for index, line in enumerate(lines)
        if re.match(r"^\s*(?:\d+[.)]|[-•*])\s+", line)
    ]
    if len(listed) < 2:
        return False
    intro = "\n".join(lines[:listed[0]])[-500:]
    if not re.search(
        r"вот\s+(?:некоторые|несколько)\s+из\s+них|"
        r"вот\s+несколько\s+[^:\n]{0,120}"
        r"(?:платформ|сервис|ресурс|вариант|школ|курс)[^:\n]{0,120}:|"
        r"(?:вариант(?:ы|ов)?|подходящие\s+(?:сервисы|ресурсы|курсы|площадки))\s*:|"
        r"(?:можно|стоит)\s+(?:рассмотреть|выбрать)\s*:",
        intro, re.I,
    ):
        return False
    for index in listed:
        item = re.sub(r"^\s*(?:\d+[.)]|[-•*])\s+", "", lines[index])
        item = re.sub(r"^[*_\s]+", "", item)
        if re.match(name, item, re.I) or re.search(
            rf"(?:платформ\w*|сервис\w*|курс\w*)\s+{name}", item, re.I
        ):
            return True
    return False


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
    option = _proposed_as_option(content, name)
    for sentence in evidence:
        # Split contrast clauses: a recommendation of B must not be attributed to A.
        clauses = re.split(r",\s*(?:но|а|but)\s+", sentence, flags=re.I)
        for clause in clauses:
            if not re.search(name, clause, re.I):
                continue
            negative_pattern = (
                r"(?:не\s+(?:рекомендую|рекомендуем|советую|советуем)|"
                rf"do\s+not\s+recommend|don't\s+recommend)\s+"
                rf"(?:(?:магазин|платформу|сервис|курсы|курс|бренд)\s+)?{name}"
            )
            positive_pattern = (
                rf"(?:рекомендую|рекомендуем|советую|советуем|recommend)\s+"
                rf"(?:(?:магазин|платформу|сервис|курсы|курс|бренд)\s+)?{name}"
            )
            reverse_pattern = (
                rf"{name}\s+(?:(?:is|was)\s+)?(?:recommended|suggested)\b|"
                rf"{name}\s+(?:рекомендуется|советуют|советуются)\b|"
                rf"{name}\s+(?:рекомендую|рекомендуем|советую|советуем)\b"
            )
            neg_reverse = rf"{name}\s+не\s+(?:рекомендую|рекомендуем|советую|советуем)\b"
            negative_passive = rf"{name}\s+(?:(?:is|was)\s+)?not\s+recommended\b"
            if (
                re.search(negative_pattern, clause, re.I)
                or re.search(neg_reverse, clause, re.I)
                or re.search(negative_passive, clause, re.I)
            ):
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
    if uncertain or (positive and negative) or (option and negative):
        status = "AMBIGUOUS"
    elif negative:
        status = "NOT_RECOMMENDED"
    elif positive:
        status = "RECOMMENDED"
    elif option:
        status = "PROPOSED_AS_OPTION"
    else:
        status = "MENTIONED"
    return BrandVerdict(status, tuple(evidence))
