import json
from collections.abc import Iterable, Iterator


def iter_sse(lines: Iterable[str]) -> Iterator[dict]:
    for line in lines:
        value = line.strip()
        if not value.startswith("data:"):
            continue
        payload = value[5:].strip()
        if payload == "[DONE]":
            return
        if payload:
            yield json.loads(payload)

