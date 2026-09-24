from types import SimpleNamespace

from sqlalchemy.dialects import sqlite

import recommendation.simulation.models  # noqa: F401 - register related ORM model
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
        for i, text in enumerate([
            "Не рекомендую Пример",
            "Рекомендую Пример",
            "",
            "Вот некоторые из них:\n1. Пример — магазин деталей\n2. Другой — магазин",
        ], 1)
    ]

    class Database:
        calls = 0
        execute_calls = 0
        statements = []

        def scalars(self, statement):
            self.calls += 1
            self.statements.append(statement)
            return [research] if self.calls == 1 else []

        def execute(self, statement):
            self.execute_calls += 1
            return SimpleNamespace(all=lambda: rows if self.execute_calls == 1 else [])

    service = object.__new__(WordstatService)
    service.db = Database()
    service.repository = SimpleNamespace(latest=lambda organization_id, brand: snapshot)
    result = service.analytics(7, "Пример")
    item = result.items[0]
    assert item.response_count == 3
    assert item.recommendation_count == 1
    assert item.option_count == 1
    assert item.excluded_response_count == 1
    assert result.weighted_visibility == 33.3
    assert item.verdicts[0]["status"] == "NOT_RECOMMENDED"
    assert item.verdicts[0]["evidence"] == ("Не рекомендую Пример",)
    assert "brand-verdict-1.3" in result.methodology_version
    compiled = Database.statements[0].compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )
    assert 'yandex_wordstat_snapshot_id' in str(compiled)
