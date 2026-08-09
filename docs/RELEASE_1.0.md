# AI Ranking OS Release 1.0

Release 1.0 publishes the isolated production installation at
`https://app.разуммаркета.рф`. It contains the authenticated Research Wizard, complete
Skinjestique pipeline and AI Visibility Report from Sprint 10/11, plus automated DNS/TLS release
gates, monitoring, daily PostgreSQL/Redis backups and disaster-recovery validation.

## Release gates

1. `dns_readiness.sh` requires authoritative, Cloudflare and Google A records to equal
   `72.56.33.7`; AAAA is intentionally omitted until the VPS has routed IPv6.
2. `enable_https.sh` obtains Let's Encrypt only after DNS passes, validates the chain, installs the
   isolated TLS vhost, tests Nginx and verifies HTTPS plus HTTP redirect.
3. `release_audit.py` checks public DNS/TLS, mandatory security headers and latency.
4. `smoke_test.py` and Playwright validate login, Skinjestique research, report and logout.

The release does not modify the existing landing or Ozon Agent. Sprint 12 is outside this release.

## Production validation

Validated on 8 August 2026 against the public endpoint:

| Gate | Result |
| --- | --- |
| DNS | PASS — A `72.56.33.7`, TTL 600, no AAAA |
| HTTPS | PASS — TLS 1.2/1.3, trusted Let's Encrypt chain, HTTP redirect |
| SSL Labs | A+ |
| Mozilla TLS baseline | PASS — modern protocols/ciphers and HSTS |
| Security headers | PASS — CSP, HSTS, clickjacking, MIME, referrer and permissions controls |
| Public API workflow | PASS — login, research, Skinjestique demo, report |
| Public Web workflow | PASS — Playwright login through logout |
| PostgreSQL restore | PASS — restored schema revision `0042` |
| Redis restore artifact | PASS — `redis-check-rdb` |
| Clean-room deployment | PASS — isolated volumes and complete smoke test |
| Regression protection | PASS — existing landing and Ozon Agent remained available |
| Automated tests | PASS — 225 tests |

The current Let's Encrypt certificate does not advertise an OCSP responder URL. Nginx is prepared
for stapling when a CA supplies one; certificate-chain and expiry validation remain automated.

## Operational limitation

Provider adapters are production-ready, but the deployed environment remains in deterministic mock
provider mode until production API credentials are provisioned. This keeps the public demo fully
reproducible and prevents unapproved external spend.
