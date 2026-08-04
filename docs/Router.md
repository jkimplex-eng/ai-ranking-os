# Production LLM Router

The Router scores every eligible model across intent fit, cost, latency, quality,
context capacity, hallucination risk, domain fit, and language fit. Policies set
weights and execution mode:

- `cost-optimized`: low-cost FALLBACK chain.
- `quality-first`: highest-quality SINGLE route.
- `latency-critical`: fastest FALLBACK chain.
- `research-grade`: research-capable ENSEMBLE.
- `multilingual`: multilingual PARALLEL plan.

Eligibility also requires ACTIVE status, sufficient context, availability,
capabilities, and a circuit that permits traffic. Circuits progress CLOSED →
OPEN → HALF_OPEN → CLOSED. Daily and monthly budget limits reorder a route
toward the lowest estimated cost and mark it as downgraded.

Use `POST /router/route` for the scored response or `POST /router/plan` for the
executor contract. Registry and policy endpoints support runtime CRUD, search,
filtering, and pagination. Every route persists its score, cost estimate, model
selection, latency, and correlation ID.
