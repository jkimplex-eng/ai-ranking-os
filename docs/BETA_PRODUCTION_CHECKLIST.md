# Closed Beta Production Checklist

## Release

- [ ] CI is green for the exact deployed commit.
- [ ] Alembic upgrade, downgrade and re-upgrade pass on PostgreSQL 16.
- [ ] Production Compose and all healthchecks pass.
- [ ] DNS, TLS, headers and public readiness are verified.
- [ ] Demo credentials are protected and scheduled for rotation.

## Operations

- [ ] PostgreSQL and Redis backups are less than 25 hours old.
- [ ] A restore drill passed in an isolated environment.
- [ ] Disk, database, Redis, certificate, queue and provider alerts are active.
- [ ] Daily operations and incident owners are assigned.
- [ ] Provider budgets and failover policy are reviewed.

## Product journey

- [ ] Invite, login and organization switching work.
- [ ] Skinjestique research completes automatically.
- [ ] Report, export and view-only sharing work.
- [ ] Completion notification and feedback submission work.
- [ ] Product Analytics receives journey events.
