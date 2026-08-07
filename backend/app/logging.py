import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import Request

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")
research_id_var: ContextVar[str] = ContextVar("research_id", default="-")
execution_id_var: ContextVar[str] = ContextVar("execution_id", default="-")
provider_var: ContextVar[str] = ContextVar("provider", default="-")


class JsonFormatter(logging.Formatter):
    """Emit one machine-readable JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
            "research_id": research_id_var.get(),
            "execution_id": execution_id_var.get(),
            "provider": provider_var.get(),
        }
        if hasattr(record, "latency_ms"):
            payload["latency_ms"] = record.latency_ms
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def bind_request(request: Request) -> str:
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request_id_var.set(request_id[:200])
    research_id_var.set(request.path_params.get("research_id", "-"))
    execution_id_var.set(request.path_params.get("execution_id", "-"))
    provider_var.set(request.headers.get("X-Provider", "-")[:100])
    return request_id
