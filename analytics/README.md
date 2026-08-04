# Analytics Engine

TASK-701 implements the provider-neutral analytical layer. The engine consumes only
`AnalyticsDataSource`, persists executions through `AnalyticsRepository`, and contains no imports
from Research or Graph.

Features:

- aggregate metrics and dimension filters;
- grouping by arbitrary public dimensions;
- hourly, daily, weekly, and monthly time buckets;
- count, sum, average, min, max, median, population standard deviation, and percentiles;
- versioned, reproducible run history with pagination.

API:

- `POST /analytics/query`
- `GET /analytics/runs`
- `GET /analytics/runs/{id}`

The current platform adapter exposes Visibility, Mention, Recommendation, Citation, Coverage, and
Confidence scores plus entity, research status, research ID, and algorithm version dimensions.

