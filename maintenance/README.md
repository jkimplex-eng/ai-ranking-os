# Operational maintenance

`RetentionService` bounds graph snapshots, completed execution history, query execution
history, and Decision Center logs. Defaults preserve at least ten graph snapshots and retain
history for 90–365 days. Invoke it from the deployment scheduler as a daily maintenance job.

Graph Search currently reads the latest normalized node/edge rows and filters aliases and
properties in Python. It performs no JSONB containment query, so a GIN index would add write
and storage cost without serving an access pattern. Existing B-tree indexes cover snapshot,
type, canonical name, edge endpoints, and retention timestamps.
