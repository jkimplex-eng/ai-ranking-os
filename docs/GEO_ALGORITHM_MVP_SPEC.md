# GEO Algorithm MVP — implementation contract

Status: Approved  
Source: `tz_geo_algorithm.html`, adapted to the existing AI Ranking OS architecture.  
Runtime: Python 3.13, FastAPI, SQLAlchemy 2, Pydantic v2, PostgreSQL 16.

## Context

The MVP estimates which publication resources are associated with a higher chance of a brand
appearing in an AI answer. AI retrieval and ranking internals are a black box. EIS is therefore a
versioned, correlation-based estimate, not proof that a publication caused a model response.

## Functional requirements

- **FR-01** The system MUST provide CRUD for publication platforms and MUST retain the source and
  evidence behind every imported metric.
- **FR-01.1** The system MUST accept normalized Ahrefs and Semrush imports without requiring those
  paid APIs to be configured.
- **FR-01.2** The system MUST accept discovered citation domains through a provider-neutral port,
  deduplicate them by normalized domain, and mark them as discovered.
- **FR-02** The system MUST store immutable, versioned Frozen Prompt Sets.
- **FR-02.1** Activating a version MUST deactivate older versions with the same code.
- **FR-02.2** Query fan-out MUST generate deterministic query instances from templates and
  variables and MUST persist the resulting texts and fingerprint.
- **FR-03** The system MUST calculate and persist heuristic EIS for a
  `publication platform × query × AI engine` combination.
- **FR-03.1** The score MUST expose raw inputs, normalized components, numerator, denominator,
  weights, contributions, platform bias, caps, exclusions, versions, and evidence status.
- **FR-03.2** `0`, `NOT_MEASURED`, `INSUFFICIENT_SAMPLE`, and `PARTIAL` MUST remain distinct.
- **FR-03.3** Batch prioritization MUST support at most 100 platforms and return P0–P3 ordering.

## Formula correction

The source formula uses weights `0.10 + 0.15 + 0.12 + 0.10 = 0.47`. Used literally, it cannot
reach the documented P0/P1 thresholds. Version `heuristic_v1.0` preserves the relative weights and
normalizes their weighted sum:

```text
base = (0.10*A + 0.15*B + 0.12*C + 0.10*D) / 0.47
EIS  = clamp(base + declared_engine_bias, 0, 100)
```

Bias values are explicitly labelled unvalidated priors and are stored in the explanation. They are
not presented as causal facts.

## Acceptance criteria

- **AC-01 (FR-01):** Given a manual or normalized import, when a platform is saved, then its domain
  is canonical, duplicate imports update the same record, and source evidence is retained.
- **AC-02 (FR-01.2):** Given duplicate discovered URLs, when discovery runs, then one platform per
  domain exists and the API reports created/updated counts.
- **AC-03 (FR-02):** Given a frozen set, when fan-out runs twice with identical variables, then both
  calls return the same fingerprint and query order.
- **AC-04 (FR-02.1):** Given two versions of a code, when the new version is activated, then only it
  remains active and frozen versions cannot be mutated.
- **AC-05 (FR-03):** Given measured inputs, when EIS is calculated, then the stored score can be
  reproduced from the returned contributions without hidden values.
- **AC-06 (FR-03.2):** Given no eligible evidence, when EIS is requested, then the response is
  `NOT_MEASURED` and does not misrepresent absence as zero.
- **AC-07 (FR-03.3):** Given a platform batch, when it is prioritized, then results are ordered by
  P0, P1, P2, P3 and descending EIS within a priority.

## Non-functional requirements

- **NFR-01:** A single heuristic calculation MUST complete within 2 seconds in the benchmark test.
- **NFR-02:** A batch of 100 platforms MUST complete within 30 seconds in the benchmark test.
- **NFR-03:** Public APIs MUST be documented by OpenAPI and use existing authentication/RBAC.
- **NFR-04:** Migration 0076 MUST support PostgreSQL upgrade and downgrade.

## Edge cases

- Invalid domains, unsupported import sources, duplicate versions, unknown platform/query IDs,
  incomplete evidence, out-of-range metrics, empty fan-out variables, and batches over 100 items.

## Out of scope for this increment

- Paid API calls to Ahrefs/Semrush, CatBoost, Two-Tower, LLM-as-a-Judge, SHAP, causal claims,
  knapsack budget optimization, and automated retraining. These require credentials or a validated
  labelled dataset and will not be simulated.
