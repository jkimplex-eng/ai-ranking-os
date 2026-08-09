import os
from enum import StrEnum


class RoutingMode(StrEnum):
    CLOUD = "CLOUD"
    LOCAL = "LOCAL"
    HYBRID = "HYBRID"


class HybridOrder(StrEnum):
    LOCAL_FREE_PAID = "LOCAL_FREE_PAID"
    LOCAL_PAID = "LOCAL_PAID"
    FREE_PAID = "FREE_PAID"


def configured_mode() -> RoutingMode:
    return RoutingMode(os.getenv("AI_ROUTING_MODE", RoutingMode.HYBRID).upper())


def configured_hybrid_order() -> HybridOrder:
    return HybridOrder(os.getenv("AI_HYBRID_ORDER", HybridOrder.LOCAL_FREE_PAID).upper())


def hybrid_tier(tier: str, input_price: float, output_price: float) -> str:
    if tier == "LOCAL":
        return "LOCAL"
    if input_price == 0 and output_price == 0:
        return "FREE"
    return "PAID"


def hybrid_rank(order: HybridOrder, tier: str) -> int | None:
    groups = {
        HybridOrder.LOCAL_FREE_PAID: ("LOCAL", "FREE", "PAID"),
        HybridOrder.LOCAL_PAID: ("LOCAL", "PAID"),
        HybridOrder.FREE_PAID: ("FREE", "PAID"),
    }[order]
    return groups.index(tier) if tier in groups else None
