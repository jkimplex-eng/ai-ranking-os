from types import SimpleNamespace

from research.models import ResponseProcessingStatus
from yandex_wordstat.service import WordstatService


def test_analytics_uses_verdict_evidence_and_excludes_empty_answers():
    query = "где купить детали"
    research = SimpleNamespace(id=1, metadata_payload={"organization_id": 7, "brand": "Пример"})
    snapshot = SimpleNamespace(
        id=8,
        brand="Пример",
        category="запчасти",
        queries=[
            dict(
                query=query,
                frequency=100,
                demand_rank=1,
                source_type="TOP",
                branded=False,
                selected_for_alice=True,
            )
        ],
    )
    task = SimpleNamespace(query=query, research_id=1)
    rows = [
        (
            SimpleNamespace(
                id=i, content=text, processing_status=ResponseProcessingStatus.PROCESSED
            ),
            task,
        )
        for i, text in enumerate(["Не рекомендую Пример", "Рекомендую Пример", ""], 1)
    ]

    class Database:
        calls = 0

        def scalars(self, statement):
            self.calls += 1
            return [research] if self.calls == 1 else []

        def execute(self, statement):
            return SimpleNamespace(all=lambda: rows)

    service = object.__new__(WordstatService)
    service.db = Database()
    service.repository = SimpleNamespace(latest=lambda organization_id, brand: snapshot)
    result = service.analytics(7, "Пример")
    item = result.items[0]
    assert item.response_count == 2
    assert item.recommendation_count == 1
    assert item.excluded_response_count == 1
    assert result.weighted_visibility == 50
    assert item.verdicts[0]["status"] == "NOT_RECOMMENDED"
    assert item.verdicts[0]["evidence"] == ("Не рекомендую Пример",)
    assert "brand-verdict-1.0" in result.methodology_version
