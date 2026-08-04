from prometheus_client import Counter, Gauge, Histogram

ROUTER_REQUESTS = Counter(
    "ai_ranking_os_router_requests_total",
    "Total LLM Router requests",
    ["policy", "status"],
)
ROUTER_LATENCY = Histogram(
    "ai_ranking_os_router_latency_seconds",
    "LLM Router selection latency",
    ["policy"],
)
ROUTER_SELECTED = Counter(
    "ai_ranking_os_router_model_selected_total",
    "Selected model count",
    ["model", "provider"],
)
ROUTER_FALLBACKS = Counter(
    "ai_ranking_os_router_fallback_total",
    "Planned fallback count",
    ["policy"],
)
ROUTER_COST = Counter(
    "ai_ranking_os_router_estimated_cost_usd_total",
    "Estimated routed cost in USD",
    ["model", "provider"],
)
ROUTER_ERRORS = Counter(
    "ai_ranking_os_router_errors_total",
    "Router errors",
    ["error_type"],
)
ROUTER_SCORE = Histogram(
    "ai_ranking_os_router_score",
    "Selected routing scores",
    ["model"],
    buckets=(0.1, 0.25, 0.5, 0.75, 0.9, 1.0),
)
CIRCUIT_STATE = Gauge(
    "ai_ranking_os_router_circuit_state",
    "Circuit state: closed=0, half_open=1, open=2",
    ["model"],
)

