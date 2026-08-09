from backend.app.llm_router.mode import HybridOrder, hybrid_rank, hybrid_tier


def test_hybrid_tier_is_provider_independent() -> None:
    assert hybrid_tier("LOCAL", 10, 10) == "LOCAL"
    assert hybrid_tier("STANDARD", 0, 0) == "FREE"
    assert hybrid_tier("PREMIUM", 1, 2) == "PAID"


def test_supported_hybrid_orders() -> None:
    assert hybrid_rank(HybridOrder.LOCAL_FREE_PAID, "LOCAL") == 0
    assert hybrid_rank(HybridOrder.LOCAL_FREE_PAID, "PAID") == 2
    assert hybrid_rank(HybridOrder.LOCAL_PAID, "FREE") is None
    assert hybrid_rank(HybridOrder.FREE_PAID, "LOCAL") is None
