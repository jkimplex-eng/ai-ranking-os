# Export Engine

TASK-704 exports persisted Analytics Engine results without depending on Research or Graph. A
public `ExportRepository` supplies flat rows; the service handles filtering, column projection,
batching, serialization, and streaming.

Formats:

- CSV with UTF-8 BOM and spreadsheet-formula injection protection;
- streaming JSON array;
- write-only XLSX streamed from a bounded spooled temporary file;
- batched Parquet streamed from a bounded spooled temporary file.

API: `POST /exports`. Multiple `analytics_run_ids` produce one batch export. `batch_size` controls
CSV flushes and Parquet record batches. No Alembic migration is required because the engine is
stateless and does not add persistence.

