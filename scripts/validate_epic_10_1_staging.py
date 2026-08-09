"""Authenticated staging smoke and queued-research load validation for EPIC 10.1."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any


def request(
    base_url: str,
    path: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    method: str | None = None,
) -> Any:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    call = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=data,
        headers=headers,
        method=method or ("POST" if data is not None else "GET"),
    )
    try:
        with urllib.request.urlopen(call, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise RuntimeError(f"{call.method} {path}: HTTP {error.code}: {detail}") from error


def run(base_url: str, email: str, password: str, count: int, profile: str) -> dict[str, Any]:
    auth = request(base_url, "/auth/login", payload={"email": email, "password": password})
    token = auth["access_token"]
    profiles = request(base_url, "/router/profiles", token=token)
    providers = request(base_url, "/providers", token=token)
    request(
        base_url,
        "/agents",
        token=token,
        payload={"name": f"epic101-staging-{int(time.time())}"},
    )

    def enqueue(index: int) -> dict[str, Any]:
        research = request(
            base_url,
            "/research",
            token=token,
            payload={"title": f"EPIC 10.1 load {profile} #{index}"},
        )
        return request(
            base_url,
            "/research/run",
            token=token,
            payload={
                "research_id": research["id"],
                "routing_profile": profile,
                "query": "Analyze the AI visibility of Skinjestique in one concise paragraph.",
            },
        )

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(count, 50)) as executor:
        jobs = list(executor.map(enqueue, range(count)))
    enqueue_seconds = time.perf_counter() - started
    deadline = time.monotonic() + max(180, count * 30)
    states: dict[int, str] = {}
    while time.monotonic() < deadline:
        states = {
            job["id"]: request(
                base_url, f"/research/jobs/{job['id']}", token=token
            )["state"]
            for job in jobs
        }
        if all(state in {"COMPLETED", "FAILED"} for state in states.values()):
            break
        time.sleep(1)
    total_seconds = time.perf_counter() - started
    summary = {
        "profile": profile,
        "requested": count,
        "completed": sum(state == "COMPLETED" for state in states.values()),
        "failed": sum(state == "FAILED" for state in states.values()),
        "pending": sum(state not in {"COMPLETED", "FAILED"} for state in states.values()),
        "enqueue_seconds": round(enqueue_seconds, 3),
        "total_seconds": round(total_seconds, 3),
        "throughput_per_second": round(count / total_seconds, 3),
        "profiles": [item["profile"] for item in profiles],
        "provider_states": {item["id"]: item["availability"] for item in providers},
    }
    if summary["failed"] or summary["pending"]:
        raise RuntimeError(json.dumps(summary, ensure_ascii=False))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18100/api")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--profile", default="PRIVATE")
    args = parser.parse_args()
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        raise SystemExit("ADMIN_EMAIL and ADMIN_PASSWORD are required")
    print(json.dumps(run(args.base_url, email, password, args.count, args.profile), indent=2))


if __name__ == "__main__":
    main()
