"""External release audit for DNS, TLS, headers, API and basic latency."""

import json
import os
import socket
import ssl
import statistics
import time
from urllib.request import Request, urlopen

DOMAIN = os.environ.get("APP_DOMAIN", "app.xn--80aaatitma6afyf.xn--p1ai")
BASE = f"https://{DOMAIN}"


def fetch(path: str):
    started = time.perf_counter()
    request = Request(BASE + path, headers={"User-Agent": "ai-ranking-release-audit"})
    with urlopen(request, timeout=30) as response:
        latency = (time.perf_counter() - started) * 1000
        return response.status, dict(response.headers), response.read(), latency


def main() -> None:
    addresses = socket.getaddrinfo(DOMAIN, 443, type=socket.SOCK_STREAM)
    resolved = sorted({item[4][0] for item in addresses})
    context = ssl.create_default_context()
    with (
        socket.create_connection((DOMAIN, 443), timeout=15) as raw,
        context.wrap_socket(raw, server_hostname=DOMAIN) as tls,
    ):
        certificate = tls.getpeercert()
        protocol = tls.version()
    latencies = []
    status, headers, body, latency = fetch("/health")
    latencies.append(latency)
    for _ in range(4):
        latencies.append(fetch("/")[3])
    required = {
        "strict-transport-security",
        "content-security-policy",
        "x-content-type-options",
        "x-frame-options",
        "referrer-policy",
        "permissions-policy",
    }
    normalized = {key.lower(): value for key, value in headers.items()}
    missing = sorted(required - normalized.keys())
    assert status == 200 and json.loads(body)["status"] == "ok"
    assert not missing, f"Missing security headers: {missing}"
    assert protocol == "TLSv1.3", protocol
    print(json.dumps({
        "status": "PASS",
        "domain": DOMAIN,
        "addresses": resolved,
        "tls": protocol,
        "certificate_expires": certificate["notAfter"],
        "headers": sorted(required),
        "latency_ms_p50": round(statistics.median(latencies), 2),
        "latency_ms_max": round(max(latencies), 2),
    }))


if __name__ == "__main__":
    main()
