# Production Runbook

## Service status

```sh
cd /opt/ai-ranking-os/deployment/production
docker compose --env-file .env ps
./scripts/monitor.sh
systemctl list-timers 'ai-ranking-*'
```

Use `/health` for liveness, `/ready` for PostgreSQL/Redis readiness and `/metrics` for Prometheus.
Logs are JSON-limited by Docker rotation. Initial credentials are root-only in
`/root/.ai-ranking-os-initial-admin` and must be rotated after handoff.

## Deploy and rollback

Back up first, deploy an immutable reviewed commit with `deploy.sh`, run public smoke and Playwright.
For application rollback set `ROLLBACK_IMAGE_TAG` to the last known-good immutable tag and execute
`rollback.sh`. Do not downgrade the database unless the migration's rollback has been reviewed and
a verified backup exists.

## Common incidents

- `/ready` database unavailable: stop deployments, inspect PostgreSQL health/logs and pool capacity.
- Redis degraded: core database operations remain available; inspect authentication, memory and AOF.
- 502 after container recreation: `deploy.sh` recreates edge Nginx to refresh upstream addresses.
- Certificate warning: run `dns_readiness.sh`, inspect Certbot renewal logs, then `enable_https.sh`.
- Disk above 85%: preserve backups, rotate application/build cache safely, then investigate growth.
