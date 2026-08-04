# Operations

Daily checks: system health, provider and circuit state, error ratio, queue
depth, validation status, token usage, and budget consumption. Review routing
history for unexpected downgrades or score shifts.

Model lifecycle:

1. Register a model as `MAINTENANCE`.
2. Verify metadata, capabilities, pricing, and health.
3. Change status to `ACTIVE`.
4. Monitor selection, latency, errors, and cost.
5. Use `DEGRADED` or `DISABLED` to remove it from new routes.
6. Delete only after history retention and dependency checks.

Policy changes should be canaried with a named policy and compared on cost,
latency, quality, and fallback rate. Preserve YAML and database backups before
large registry changes.
