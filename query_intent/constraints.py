import re

from query_intent.schemas import ConstraintResult

CONSTRAINT_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "PRICE",
        "LTE",
        re.compile(
            r"(?:under|below|up to|до|не дороже)\s*([$€£₽]?\s*\d[\d,.]*)",
            re.I,
        ),
    ),
    (
        "PRICE",
        "GTE",
        re.compile(r"(?:over|above|от)\s*([$€£₽]?\s*\d[\d,.]*)", re.I),
    ),
    (
        "QUANTITY",
        "EQ",
        re.compile(r"\b(?:top|топ)\s*(\d+)\b", re.I),
    ),
    (
        "TIME",
        "EQ",
        re.compile(r"\b(?:today|tomorrow|сегодня|завтра|this week)\b", re.I),
    ),
    (
        "LOCATION",
        "EQ",
        re.compile(r"\b(?:in|near|в|рядом с)\s+([A-ZА-Я][\w-]+(?:\s+[A-ZА-Я][\w-]+)?)"),
    ),
)


def extract_constraints(query: str, language: str) -> list[ConstraintResult]:
    constraints: list[ConstraintResult] = []
    for constraint_type, operator, pattern in CONSTRAINT_PATTERNS:
        for match in pattern.finditer(query):
            value = match.group(1) if match.lastindex else match.group()
            constraints.append(
                ConstraintResult(
                    constraint_type=constraint_type,
                    operator=operator,
                    value=value.strip(),
                    confidence=0.85,
                )
            )
    constraints.append(
        ConstraintResult(
            constraint_type="LANGUAGE",
            operator="EQ",
            value=language,
            confidence=1.0,
        )
    )
    return constraints

