"""Production smoke test through the public Web edge, without Swagger/Postman."""

import json
import os
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8100").rstrip("/")


def call(path: str, *, method: str = "GET", payload=None, token: str | None = None):
    headers = {"Accept": "application/json", "X-Request-ID": "production-smoke-test"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        request = Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
        # Local providers execute the full query matrix synchronously in v1.1.
        # Keep the release smoke above the production proxy budget.
        with urlopen(request, timeout=900) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"{path}: HTTP {error.code}: {error.read().decode()}") from error


def wait_for_research(research_id: int, token: str) -> dict:
    deadline = time.monotonic() + int(os.environ.get("SMOKE_RESEARCH_TIMEOUT_SECONDS", "180"))
    while True:
        status, research = call(f"/api/research/{research_id}", token=token)
        if status != 200:
            raise RuntimeError(f"Research {research_id} status request returned HTTP {status}")
        state = research.get("status")
        if state == "COMPLETED":
            return research
        if state == "FAILED":
            raise RuntimeError(f"Research {research_id} failed in the worker")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Research {research_id} stayed in {state} beyond smoke timeout")
        time.sleep(2)


def main() -> None:
    email = os.environ["SMOKE_EMAIL"]
    password = os.environ["SMOKE_PASSWORD"]
    status, health = call("/health")
    assert status == 200 and health["status"] == "ok"
    status, readiness = call("/ready")
    assert status == 200 and readiness["database"] == "available"
    status, tokens = call(
        "/api/auth/login",
        method="POST",
        payload={"email": email, "password": password},
    )
    assert status == 200
    token = tokens["access_token"]
    provider = os.environ.get("SMOKE_PROVIDER", "openai")
    model = os.environ.get("SMOKE_MODEL", "gpt-4o-mini")
    website_url = os.environ.get("SMOKE_WEBSITE_URL", "https://skinjestique.ru")
    payload = {
        "brand": "Skinjestique",
        "website_url": website_url,
        "models": [{"provider": provider, "model": model}],
        "languages": ["en"],
        "regions": ["GLOBAL"],
        "prompt_code": "ai-visibility",
        "research_template_code": "ai-visibility",
        "brand_profile": {
            "version": "1.0",
            "brand": "Skinjestique",
            "website_url": website_url,
            "pages_analyzed": 1,
            "evidence_urls": [website_url],
            "description": "Skinjestique beauty brand",
            "categories": ["cosmetics"],
            "products": [{"name": "Hydrating Serum"}],
            "attributes": ["hydrating"],
            "confidence": 0.8,
            "limitations": [],
        },
    }
    status, review = call(
        "/api/research/wizard/review", method="POST", payload=payload, token=token
    )
    assert status == 200 and review["valid"] is True
    status, result = call("/api/research/wizard/run", method="POST", payload=payload, token=token)
    assert status == 201
    research_id = result["research"]["id"]
    if result["research"]["status"] != "COMPLETED":
        wait_for_research(research_id, token)
    report_status, report = call(f"/api{result['report_url']}", token=token)
    assert report_status == 200 and report["score"]["visibility_score"] >= 0
    print(
        json.dumps(
            {
                "status": "PASS",
                "research_id": research_id,
                "report_url": result["report_url"],
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}), file=sys.stderr)
        raise
