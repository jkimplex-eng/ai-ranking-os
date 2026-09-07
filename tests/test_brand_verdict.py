import pytest

from research.brand_verdict import VERSION, classify_brand


@pytest.mark.parametrize(
    "text,brand,status",
    [
        ("Не рекомендую АвтоПример", "АвтоПример", "NOT_RECOMMENDED"),
        ("АвтоПример не советую", "АвтоПример", "NOT_RECOMMENDED"),
        ("Рекомендую АвтоПример", "АвтоПример", "RECOMMENDED"),
        ("Советуем **АвтоПример**", "АвтоПример", "RECOMMENDED"),
        ("Не рекомендую АвтоПример, а рекомендую Другой", "АвтоПример", "NOT_RECOMMENDED"),
        ("Не рекомендую АвтоПример, а рекомендую Другой", "Другой", "RECOMMENDED"),
        ("АвтоПример продаёт детали. Рекомендую Другой", "АвтоПример", "MENTIONED"),
        ("Если нужен самовывоз, рекомендую АвтоПример", "АвтоПример", "AMBIGUOUS"),
        ("Не могу сказать, что рекомендую АвтоПример", "АвтоПример", "AMBIGUOUS"),
        ("Рекомендую АвтоПример. Не рекомендую АвтоПример", "АвтоПример", "AMBIGUOUS"),
        ("1. АвтоПример — магазин запчастей", "АвтоПример", "MENTIONED"),
        ("Рекомендую АвтоПримерПлюс", "АвтоПример", "NOT_MENTIONED"),
        ("I do not recommend Example", "Example", "NOT_RECOMMENDED"),
        ("I recommend Example", "Example", "RECOMMENDED"),
        ("Рекомендую магазин АвтоПример", "АвтоПример", "AMBIGUOUS"),
        ("", "АвтоПример", "NOT_MEASURED"),
        ("Рекомендую магазин", "", "NOT_MEASURED"),
    ],
)
def test_brand_verdict_is_scoped_and_conservative(text, brand, status):
    verdict = classify_brand(text, brand)
    assert verdict.status == status
    assert verdict.version == VERSION
    if status not in {"NOT_MEASURED", "NOT_MENTIONED"}:
        assert verdict.evidence
