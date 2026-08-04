from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "ai_ranking_os_http_requests_total",
    "HTTP requests",
    ["method", "path", "status"],
)
HTTP_LATENCY = Histogram(
    "ai_ranking_os_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)
PIPELINE_STATUS = Gauge(
    "ai_ranking_os_pipeline_validation_status",
    "Latest pipeline validation status (1=pass)",
)
QUEUE_DEPTH = Gauge(
    "ai_ranking_os_queue_depth",
    "READY task queue depth",
)
COMPONENT_RECORDS = Gauge(
    "ai_ranking_os_component_records",
    "Persisted records by component",
    ["component"],
)
BACKEND_ERRORS = Counter(
    "ai_ranking_os_backend_errors_total",
    "Backend errors that triggered resilience handling",
    ["backend", "operation"],
)
BACKEND_AVAILABLE = Gauge(
    "ai_ranking_os_backend_available",
    "Latest backend health state (1=available)",
    ["backend"],
)
