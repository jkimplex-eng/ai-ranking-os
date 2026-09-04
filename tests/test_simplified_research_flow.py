from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from alice_learning.automation_schemas import AutomationPlanCreate
from alice_learning.automation_service import AliceAutomationService
from product.schemas import WizardRequest


def test_wizard_accepts_supported_wordstat_query_limits() -> None:
    for limit in (30, 50, 100):
        payload = WizardRequest(
            brand="Skillbox",
            website_url="https://skillbox.ru",
            query_limit=limit,
        )
        assert payload.query_limit == limit

    with pytest.raises(ValidationError):
        WizardRequest(
            brand="Skillbox",
            website_url="https://skillbox.ru",
            query_limit=101,
        )


def test_monitoring_cadence_is_explicit_and_changes_next_run() -> None:
    now = datetime(2026, 9, 3, 12, tzinfo=UTC)
    assert AutomationPlanCreate(
        template_research_id=1,
        brand="Skillbox",
        website_url="https://skillbox.ru",
    ).monitoring_frequency == "DAILY"
    assert AliceAutomationService._next_run(now, "DAILY") == datetime(
        2026, 9, 4, 3, tzinfo=UTC
    )
    assert AliceAutomationService._next_run(now, "WEEKLY") == datetime(
        2026, 9, 10, 3, tzinfo=UTC
    )
