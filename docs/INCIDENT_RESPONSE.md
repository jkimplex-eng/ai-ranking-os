# Incident Response

## Severity

- **SEV-1:** public outage, data loss, credential compromise or corrupted reports.
- **SEV-2:** degraded pipeline/provider, failed backups, sustained errors or severe latency.
- **SEV-3:** isolated defect without material customer impact.

## Response

1. Declare severity, timestamp and incident owner; preserve correlation/request IDs.
2. Contain: disable affected provider or block traffic without altering the legacy website.
3. Diagnose using Nginx access/error logs, JSON application logs, container health, PostgreSQL/Redis
   status and recent deploy history.
4. Recover with immutable rollback or verified PostgreSQL/Redis restore.
5. Validate `/health`, `/ready`, authentication, Skinjestique pipeline, report and logout.
6. Document impact, timeline, root cause, remediation and prevention.

Never paste secrets or customer responses into tickets or chat. Rotate credentials immediately if
exposure is suspected. Keep forensic logs and backups immutable until the incident is closed.
