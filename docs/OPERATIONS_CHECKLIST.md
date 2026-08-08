# Operations Checklist

## Daily

- [ ] All production containers healthy.
- [ ] `/ready` reports PostgreSQL and Redis available.
- [ ] PostgreSQL and Redis backups are less than 25 hours old.
- [ ] Disk utilisation is below 85%.
- [ ] Provider, queue and scheduler metrics are within baseline.
- [ ] No repeated authentication, 5xx or provider errors.

## Weekly

- [ ] Review latency, token usage and provider costs.
- [ ] Run authenticated Skinjestique smoke test.
- [ ] Verify certificate has more than 14 days remaining.
- [ ] Review Nginx, Docker and application security updates.

## Monthly

- [ ] Run `dr_validate.sh`.
- [ ] Restore PostgreSQL into the isolated validation database.
- [ ] Validate Redis RDB with `redis-check-rdb`.
- [ ] Test immutable image rollback and record recovery time.
- [ ] Review access, API keys, secrets and incident contacts.

Import `deployment/production/monitoring/uptime-dashboard.json` into the Prometheus-compatible
Grafana instance used by operations.
