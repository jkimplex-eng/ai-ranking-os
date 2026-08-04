from typing import Any

from backend.app.providers.factory import factory


def provider_health() -> list[dict[str, Any]]:
    return [
        provider.health()
        for provider in factory.all()
    ]
