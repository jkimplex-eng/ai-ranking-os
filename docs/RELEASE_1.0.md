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
