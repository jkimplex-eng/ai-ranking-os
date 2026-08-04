# Cache
Backend-neutral TTL and tag cache with invalidation, warming, statistics, read-through and
write-through services. Redis is the production adapter; memory is deterministic for tests.

The API uses a resilient facade. Redis failures open a circuit after three errors and safely
degrade cache operations to process-local memory; cache unavailability never blocks business
requests. `/cache/stats` exposes `degraded`, backend selection, and backend error count.
