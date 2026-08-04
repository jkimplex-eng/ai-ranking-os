# Configuration

`config/router.yaml` controls defaults, circuit thresholds, timeouts, and
budgets. `config/providers.yaml` defines model health, pricing, latency, quality,
context, capabilities, domains, and languages. `config/policies.yaml` defines
routing weights and modes. `config/monitoring.yaml` defines SLOs, scrape
behavior, and alert thresholds.

Configuration is reloaded when a YAML modification time changes; recompilation
is not required. Model and policy API updates take effect immediately in the
database and override bootstrap values.

Environment variables configure the database, Redis, application version,
build SHA, release channel, log level, retry timing, and provider credentials.
Start from `.env.example`. Validate policy weights sum to `1.0` before rollout.
