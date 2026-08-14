# Publication Learning Engine

The module learns observed publication effects from matched before/after research matrices.
It stores immutable experiments and versioned aggregate estimates by resource domain, channel,
content type, provider/model, category, language and region.

It never treats a single correlation as causality. A baseline must use the same prompts, models,
language and region as the follow-up. Confidence increases only with repeated observations.

API:

- `POST /publication-learning/evaluate/{research_id}`
- `GET /publication-learning/entity/{entity_id}`
- `GET /publication-learning/influence`
