# Change Detection

Versioned deterministic comparison of consecutive Research snapshots. The module owns
persisted change results and reads normalized score, recommendation, citation and Knowledge
Graph facts through `ChangeSnapshotSource`. Product orchestration triggers it after the full
pipeline completes.
