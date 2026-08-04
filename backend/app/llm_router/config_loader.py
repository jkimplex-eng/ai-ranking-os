from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_ROOT = PROJECT_ROOT / "config"


@lru_cache(maxsize=16)
def _read_cached(path: str, modified_ns: int) -> dict[str, Any]:
    del modified_ns
    with Path(path).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def load_config(name: str) -> dict[str, Any]:
    path = CONFIG_ROOT / name
    return _read_cached(str(path), path.stat().st_mtime_ns)


def router_config() -> dict[str, Any]:
    return load_config("router.yaml")


def provider_config() -> dict[str, Any]:
    return load_config("providers.yaml")


def policy_config() -> dict[str, Any]:
    return load_config("policies.yaml")


def monitoring_config() -> dict[str, Any]:
    return load_config("monitoring.yaml")

