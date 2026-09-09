from closed_beta.service import ClosedBetaService


def test_tariff_catalog_has_ordered_customer_limits() -> None:
    tariffs = {item.code: item for item in ClosedBetaService.tariffs()}

    assert {"trial", "start", "growth", "business"} == tariffs.keys()
    assert tariffs["trial"].monthly_price_rub == 0
    assert tariffs["start"].monthly_price_rub > 0
    assert (
        tariffs["growth"].limits.monthly_research_limit
        > tariffs["start"].limits.monthly_research_limit
    )
    assert tariffs["business"].limits.max_projects > tariffs["growth"].limits.max_projects
