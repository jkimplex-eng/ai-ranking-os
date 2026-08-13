from product.brand_intelligence import BrandIntelligenceEngine
from product.research_intelligence import (
    CompetitiveInfluenceEngine,
    GeoOpportunityPlanner,
    QueryMapBuilder,
    ResearchPatternAnalyzer,
)


class FakeFetcher:
    def fetch(self, url: str) -> tuple[str, str]:
        return (
            url,
            """<html><head><meta name='description' content='Уход для чувствительной кожи'></head>
        <body><h1>Сыворотки и кремы</h1><script type='application/ld+json'>
        {"@type":"Product","name":"Hydra Serum","category":"Сыворотки",
        "description":"Увлажняющий уход с гиалуроновой кислотой",
        "offers":{"price":"1900","priceCurrency":"RUB"}}
        </script></body></html>""",
        )


def test_brand_intelligence_extracts_product_price_and_attributes() -> None:
    profile = BrandIntelligenceEngine(FakeFetcher(), max_pages=1).analyze(
        brand="Skinjestique", website_url="https://skinjestique.example"
    )
    assert profile["products"][0]["name"] == "Hydra Serum"
    assert profile["products"][0]["price"] == "1900"
    assert "Сыворотки" in profile["categories"]
    assert "гиалуроновая кислота" in profile["attributes"]
    assert "Сыворотки" in profile["categories"]


def test_query_map_uses_brand_products_for_narrow_queries() -> None:
    catalog = QueryMapBuilder().build(
        brand="Skinjestique",
        language="ru",
        region="RU",
        profile="BEAUTY",
        variables={},
        brand_profile={
            "categories": ["Сыворотки"],
            "products": [{"name": "Hydra Serum"}],
            "attributes": ["увлажняющий"],
        },
    )
    assert any(
        "Hydra Serum" in item.text and "цене и характеристикам" in item.text for item in catalog
    )
    assert any("увлажняющий" in item.text for item in catalog)


def test_competitive_influence_matches_price_features_and_marks_correlation() -> None:
    result = CompetitiveInfluenceEngine().compare(
        target_profile={
            "products": [
                {
                    "name": "Hydra Serum",
                    "category": "serum",
                    "description": "hydrating hyaluronic",
                    "price": 1900,
                    "currency": "RUB",
                    "evidence_url": "https://target/p",
                }
            ]
        },
        competitor_profiles=[
            {
                "brand": "Rival",
                "website_url": "https://rival",
                "products": [
                    {
                        "name": "Aqua Serum",
                        "category": "serum",
                        "description": "hydrating hyaluronic",
                        "price": 2200,
                        "currency": "RUB",
                        "evidence_url": "https://rival/p",
                    }
                ],
                "evidence_urls": ["https://rival/p"],
                "confidence": 0.8,
            }
        ],
        patterns={
            "competitors": [{"name": "Rival", "response_count": 3}],
            "source_patterns": [{"resource": "media.example", "response_count": 2}],
        },
    )
    match = result["competitors"][0]["matched_products"][0]
    assert match["target_price"] == 1900
    assert match["competitor_price"] == 2200
    assert result["source_influence"][0]["relationship"] == "OBSERVED_ASSOCIATION"
    assert result["causality_status"] == "NOT_ESTABLISHED"


def test_query_map_covers_demand_intents() -> None:
    catalog = QueryMapBuilder().build(
        brand="Skinjestique",
        language="ru",
        region="RU",
        profile="BEAUTY",
        variables={"category": "уход за проблемной кожей"},
    )
    assert len(catalog) == 8
    assert {item.cluster for item in catalog} == {
        "brand",
        "category",
        "recommendation",
        "problem",
        "comparison",
        "trust",
        "commercial",
        "evidence",
    }
    assert len({item.id for item in catalog}) == len(catalog)


def test_query_map_localizes_default_context_to_english() -> None:
    catalog = QueryMapBuilder().build(
        brand="Skinjestique",
        language="en",
        region="GLOBAL",
        profile="GEO",
        variables={},
    )

    assert all("продукт" not in item.text and "покупател" not in item.text for item in catalog)
    assert any("products and services" in item.text for item in catalog)


def test_patterns_and_opportunities_are_evidence_backed() -> None:
    query = {
        "id": "q1",
        "cluster": "recommendation",
        "intent": "recommendation",
        "text": "Что рекомендуете?",
    }
    patterns = ResearchPatternAnalyzer().analyze(
        brand="Skinjestique",
        query_catalog=[query],
        responses=[
            {
                "id": 1,
                "provider": "ollama",
                "model": "qwen2.5:3b",
                "prompt": query["text"],
                "content": "Рекомендуется Competitor A",
                "error_type": None,
            }
        ],
        entities=[
            {
                "response_id": 1,
                "name": "Competitor A",
                "canonical_name": "Competitor A",
                "entity_type": "BRAND",
            }
        ],
        citations=[
            {
                "response_id": 1,
                "url": "https://industry.example/review",
                "source": "Industry",
                "title": "Review",
            }
        ],
    )
    assert len(patterns["deficit_queries"]) == 1
    assert patterns["competitors"][0]["name"] == "Competitor A"
    assert patterns["source_patterns"][0]["resource"] == "industry.example"
    opportunities = GeoOpportunityPlanner().build(patterns)
    assert opportunities[0]["resource"] == "industry.example"
    assert all("causality_notice" in item for item in opportunities)


def test_empty_sources_produce_honest_resource_categories() -> None:
    patterns = {
        "sample": {"responses": 1},
        "deficit_queries": [],
        "source_patterns": [],
        "competitors": [],
    }
    opportunities = GeoOpportunityPlanner().build(patterns)
    assert opportunities[0]["resource"].startswith("Официальный сайт")
    assert all("конкретные домены" not in item["resource"] for item in opportunities)
