from types import SimpleNamespace

from geo_platforms.models import GeoPlatform
from product.service import ProductPipeline
# ProductPipeline instantiates ORM entities.  Load this relationship target so
# this focused test does not depend on imports performed by unrelated tests.
from recommendation.simulation.models import RecommendationSimulation  # noqa: F401


class _Db:
    def __init__(self) -> None:
        self.added: list[GeoPlatform] = []

    def scalar(self, _statement: object) -> None:
        return None

    def add(self, item: GeoPlatform) -> None:
        self.added.append(item)


def test_yandex_sources_become_observed_publication_candidates() -> None:
    db = _Db()
    pipeline = ProductPipeline(db)  # type: ignore[arg-type]
    pipeline._materialize_yandex_publication_candidates(
        SimpleNamespace(id=42),
        {
            "status": "MEASURED",
            "source_patterns": [
                {
                    "domain": "example.ru",
                    "used_in_answers": 3,
                    "coverage_percent": 60.0,
                    "confidence": "HIGH",
                    "interpretation": "Observed in official Yandex responses.",
                    "evidence": [
                        {
                            "query": "как выбрать крем для лица",
                            "url": "https://example.ru/article",
                            "title": "Guide",
                        }
                    ],
                }
            ],
        },
    )

    assert len(db.added) == 1
    candidate = db.added[0]
    assert candidate.source == "YANDEX_SEARCH_GENERATIVE"
    assert candidate.source_reference == "research:42"
    assert candidate.evidence["status"] == "OBSERVED"
    assert candidate.evidence["suggested_topic"] == (
        "Материал, который полно отвечает на запрос: «как выбрать крем для лица»."
    )
    assert candidate.evidence["source_observations"] == [{
        "query": "как выбрать крем для лица",
        "url": "https://example.ru/article",
        "title": "Guide",
    }]
    assert candidate.evidence["publication_task"]["editorial_status"] == "NOT_CHECKED"
