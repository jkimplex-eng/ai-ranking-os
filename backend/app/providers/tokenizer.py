import math


def estimate_tokens(value: str) -> int:
    """Provider-neutral conservative token estimate for preflight decisions."""

    if not value:
        return 0
    return max(1, math.ceil(len(value.encode("utf-8")) / 4))

