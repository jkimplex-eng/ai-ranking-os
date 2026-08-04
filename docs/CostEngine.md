# Cost Engine

`config/pricing.yaml` defines input and output rates per million tokens and
currency for every model. Preflight routing uses conservative UTF-8 token
estimation. Provider responses replace estimates with reported prompt and
completion token counts where available.

Every usage record contains prompt, completion and total tokens, estimated cost,
currency, provider, model and timestamp. `/system/costs` returns routed
estimates, actual recorded provider tokens, and spend grouped by provider and
currency. Prometheus exports per-provider/model token and cost counters.

Daily and monthly Router budgets remain policy controls. When predicted spend
exceeds either limit, candidates are reordered by estimated cost and the route
is marked `budget_downgraded`.

Pricing changes require no rebuild: update `config/pricing.yaml`. Treat prices
as operational configuration and review them against provider invoices.
