# Production query plan verification

Run after representative staging data is loaded; `EXPLAIN ANALYZE` against an empty database
does not provide useful production evidence.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM graph_snapshots ORDER BY created_at DESC, id DESC LIMIT 1;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM executions
WHERE state IN ('COMPLETED', 'FAILED', 'CANCELLED') AND finished_at < now() - interval '90 days';

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM execution_logs WHERE created_at < now() - interval '365 days';
```

Expected plans use `ix_graph_snapshots_created`, `ix_executions_state_finished_at`, and
`ix_execution_logs_created_at`. Record staging plans before the production rollout.
