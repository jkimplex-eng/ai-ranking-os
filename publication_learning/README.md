# Publication Learning Engine

The module learns observed publication effects from matched before/after research matrices.
It stores immutable experiments and versioned aggregate estimates by resource domain, channel,
content type, provider/model, category, language and region.

It never treats a single correlation as causality. A baseline must use the same prompts, models,
language and region as the follow-up. Confidence increases only with repeated observations.

Version 1.1 persists a response-level evidence matrix for every matched before/after pair. A
publication contributes to a venue estimate only after its URL is observed in an eligible model
response. Evidence progresses from `HYPOTHESIS` to `OBSERVATION` and, after at least three
repeatable observations, to `CORRELATION`. `EXPERIMENT` is reserved for future explicitly
controlled interventions and is never assigned automatically.

Version 1.2 adds a query-level control group. The user marks the frozen queries that a publication
is intended to affect; unchanged queries in the same research matrix become controls. For mention,
recommendation and citation metrics the service calculates a difference-in-differences estimate:

`target change - control change`

This reduces provider-wide drift and sampling noise. Controlled results are labelled
`CONTROLLED_ASSOCIATION`, never causal proof. Raw visibility remains a before/after measurement
because the aggregate weighted score cannot be reconstructed from only a subset of queries without
changing the scoring contract. Every estimate exposes its method, treatment/control pair counts,
confidence, limitations and algorithm version. Historical v1.1 estimates remain immutable.

API:

- `POST /publication-learning/evaluate/{research_id}`
- `GET /publication-learning/entity/{entity_id}`
- `GET /publication-learning/influence`
- `GET /publication-learning/experiments/{experiment_id}`
