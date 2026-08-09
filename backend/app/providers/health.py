from concurrent.futures import ThreadPoolExecutor
from typing import Any

from backend.app.providers.base import Provider
from backend.app.providers.factory import factory


def check_all(providers: list[Provider]) -> list[dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=max(1, len(providers))) as executor:
        return list(executor.map(lambda provider: provider.health(), providers))


def provider_health() -> list[dict[str, Any]]:
    return check_all(factory.all())

