from pathlib import Path
from threading import RLock
from typing import Any

import yaml

from backend.app.providers.base import ProviderModel
from backend.app.providers.capabilities import Capability, ModelCapabilities, Region
from backend.app.providers.pricing import ModelPrice

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ProviderDefinition:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.name = raw["name"]
        self.region = Region(raw["region"])
        self.protocol = raw.get("protocol", "openai")
        self.base_url = raw["base_url"].rstrip("/")
        self.credential = raw.get("credential")
        self.project_credential = raw.get("project_credential")
        self.enabled = bool(raw.get("enabled", True))
        self.mock = bool(raw.get("mock", False))
        self.timeout_seconds = float(raw.get("timeout_seconds", 30))
        self.rate_limits = raw.get("rate_limits", {})
        self._models = raw.get("models", [])

    def models(self, prices: dict[tuple[str, str], ModelPrice]) -> list[ProviderModel]:
        return [
            ProviderModel(
                id=model["id"],
                region=self.region,
                capabilities=ModelCapabilities(
                    context_window=model["context_window"],
                    max_output_tokens=model.get("max_output_tokens", 4096),
                    temperature_min=model.get("temperature_min", 0),
                    temperature_max=model.get("temperature_max", 2),
                    features={Capability(value) for value in model.get("capabilities", [])},
                ),
                price=prices[(self.name, model["id"])],
            )
            for model in self._models
        ]


class ProviderRegistry:
    def __init__(self, config_root: Path | None = None) -> None:
        self.config_root = config_root or PROJECT_ROOT / "config"
        self._lock = RLock()
        self._signature: tuple[int, int] | None = None
        self._definitions: dict[str, ProviderDefinition] = {}
        self._prices: dict[tuple[str, str], ModelPrice] = {}

    def refresh(self) -> None:
        provider_path = self.config_root / "providers.yaml"
        pricing_path = self.config_root / "pricing.yaml"
        signature = (provider_path.stat().st_mtime_ns, pricing_path.stat().st_mtime_ns)
        with self._lock:
            if signature == self._signature:
                return
            providers = yaml.safe_load(provider_path.read_text(encoding="utf-8")) or {}
            pricing = yaml.safe_load(pricing_path.read_text(encoding="utf-8")) or {}
            self._prices = {
                (item["provider"], item["model"]): ModelPrice.model_validate(item)
                for item in pricing.get("models", [])
            }
            self._definitions = {
                item["name"]: ProviderDefinition(item)
                for item in providers.get("providers", [])
            }
            self._signature = signature

    def get(self, name: str) -> ProviderDefinition:
        self.refresh()
        try:
            return self._definitions[name.casefold()]
        except KeyError as error:
            raise KeyError(f"Unknown provider: {name}") from error

    def all(self) -> list[ProviderDefinition]:
        self.refresh()
        return list(self._definitions.values())

    def enabled(self) -> list[ProviderDefinition]:
        return [definition for definition in self.all() if definition.enabled]

    def prices(self) -> dict[tuple[str, str], ModelPrice]:
        self.refresh()
        return dict(self._prices)


registry = ProviderRegistry()

