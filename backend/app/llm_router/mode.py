import os
from enum import StrEnum


class RoutingMode(StrEnum):
    CLOUD = "CLOUD"
    LOCAL = "LOCAL"
    HYBRID = "HYBRID"


def configured_mode() -> RoutingMode:
    return RoutingMode(os.getenv("AI_ROUTING_MODE", RoutingMode.HYBRID).upper())
