from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter(
    "ai_ranking_os_provider_requests_total",
    "Provider requests",
    ["provider", "model", "status"],
)
LATENCY = Histogram(
    "ai_ranking_os_provider_latency_seconds",
    "Provider latency",
    ["provider", "model"],
)
ERRORS = Counter(
    "ai_ranking_os_provider_errors_total",
    "Provider errors",
    ["provider", "category"],
)
TIMEOUTS = Counter(
    "ai_ranking_os_provider_timeouts_total",
    "Provider timeouts",
    ["provider"],
)
RETRIES = Counter(
    "ai_ranking_os_provider_retries_total",
    "Provider retries",
    ["provider"],
)
TOKENS = Counter(
    "ai_ranking_os_provider_tokens_total",
    "Provider tokens",
    ["provider", "model", "kind"],
)
COST = Counter(
    "ai_ranking_os_provider_cost_total",
    "Provider cost",
    ["provider", "model", "currency"],
)
CACHE = Counter(
    "ai_ranking_os_provider_cache_total",
    "Provider cache operations",
    ["provider", "result"],
)
IN_FLIGHT = Gauge(
    "ai_ranking_os_provider_in_flight",
    "Provider requests in flight",
    ["provider"],
)
AVAILABILITY = Gauge(
    "ai_ranking_os_provider_availability",
    "Provider health state",
    ["provider"],
)

