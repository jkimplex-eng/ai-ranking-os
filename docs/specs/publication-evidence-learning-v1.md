# Publication Evidence Learning v1

**Status:** Approved

**Date:** 2026-08-19
**Source:** GEO technical specification, reduced to the existing AI Ranking OS architecture.

## Context

AI Ranking OS already records publications, matched before/after research and aggregate influence
estimates. The learning result must now be reproducible from response-level evidence and must not
treat timing alone as evidence that a publication influenced an AI answer.

## Functional requirements

- **FR-1:** The system MUST persist the matched baseline/follow-up response matrix used by every
  publication experiment.
- **FR-2:** Every evidence row MUST expose research, task, response, query, provider, model,
  processing status, mention, recommendation and citation signals.
- **FR-3:** The system MUST classify evidence as `HYPOTHESIS`, `OBSERVATION`, `CORRELATION` or
  `EXPERIMENT`; it MUST NOT assign `EXPERIMENT` automatically.
- **FR-4:** A publication not observed in an eligible model response MUST remain a hypothesis and
  MUST NOT contribute to learned venue influence.
- **FR-5:** Influence estimates MUST expose sample size, positive/negative/neutral observations,
  confidence range, confidence score, last observation time, methodology version and limitations.
- **FR-6:** The entity learning API MUST expose experiment summaries, and a detail endpoint MUST
  expose the evidence matrix.
- **FR-7:** The GEO opportunities UI MUST display learned influence for matching venue domains and
  clearly distinguish it from heuristic EIS.
- **FR-8:** Existing APIs and historical records MUST remain readable.

## Non-functional requirements

- **NFR-1:** No new infrastructure dependency is allowed.
- **NFR-2:** Alembic upgrade and downgrade MUST be reversible.
- **NFR-3:** Evidence and aggregate calculations MUST be deterministic.
- **NFR-4:** All displayed claims MUST state that correlation does not guarantee causation.

## Acceptance criteria

- **AC-1 (FR-1, FR-2):** Given identical baseline and follow-up matrices, when a publication is
  evaluated, then the stored experiment contains paired response evidence and explicit failures.
- **AC-2 (FR-3, FR-4):** Given a publication URL absent from follow-up answers, when evaluated,
  then its level is `HYPOTHESIS` and no venue estimate is produced from it.
- **AC-3 (FR-3, FR-5):** Given repeated observed experiments for a domain, when estimates are
  rebuilt, then the result reports polarity counts, a bounded interval and `CORRELATION` evidence.
- **AC-4 (FR-6):** Given an existing experiment, its detail endpoint returns the complete evidence
  matrix; an unknown ID returns 404.
- **AC-5 (FR-7):** Given a GEO platform whose domain has learned estimates, its card displays the
  learned range, observation count and evidence level separately from EIS.
- **AC-6 (NFR-2):** Migration 0077 upgrades and downgrades without data loss outside its columns.

## Edge cases

- **EC-1:** Failed or missing responses remain visible as exclusions and do not become positive
  evidence.
- **EC-2:** Changed prompts/models/language/region prevent baseline matching.
- **EC-3:** One observation receives a deliberately wide confidence interval.
- **EC-4:** Historical 0075 rows use safe defaults and remain serializable.

## API contracts

- `GET /publication-learning/experiments/{experiment_id}` returns an experiment including
  `evidence_matrix`, counts, confidence and limitations.
- Existing `GET /publication-learning/entity/{entity_id}` and
  `GET /publication-learning/influence` add only backward-compatible fields.

## Data model additions

`publication_learning_experiments`: evidence level, response counts, matched pair count, failed
response count, confidence score/method, evidence matrix and limitations.

`publication_influence_estimates`: positive/negative/neutral experiment counts, last observation,
evidence level and limitations.

## Out of scope

- ClickHouse, MinIO, Celery and Kubernetes.
- CatBoost, Two-Tower, Double ML and automated causal claims.
- Paid SEO data imports or invented authority values.
- Guaranteed visibility increases.
