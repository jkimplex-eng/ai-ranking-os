import os

from backend.app.providers.transport import HTTPTransport
from provider_registry.schemas import ProviderCreate


class HttpProviderCatalogSource:
    def __init__(self, url: str | None = None, transport: HTTPTransport | None = None) -> None:
        self.url = url or os.getenv("PROVIDER_CATALOG_URL", "")
        self.transport = transport or HTTPTransport(10, max_retries=1)

    def fetch(self) -> list[ProviderCreate]:
        if not self.url:
            return []
        payload = self.transport.request("GET", self.url, headers={})
        return [
            ProviderCreate(
                id=str(item["id"]).casefold(),
                display_name=item.get("display_name", item["id"]),
                capabilities=item.get("capabilities", ["chat"]),
                pricing=item.get("pricing", {"source": self.url}),
                context_window=int(item.get("context_window", 4096)),
                vision=bool(item.get("vision", False)),
                embeddings=bool(item.get("embeddings", False)),
                reasoning=bool(item.get("reasoning", False)),
                tools=bool(item.get("tools", False)),
                json_mode=bool(item.get("json_mode", False)),
                streaming=bool(item.get("streaming", True)),
                free_tier=bool(item.get("free_tier", True)),
                priority=int(item.get("priority", 500)),
                metadata={"catalog_source": self.url, **item.get("metadata", {})},
            )
            for item in payload.get("providers", [])
        ]
