# EPIC-013 Phase 2 — Research Core Completion

**Author:** Codex · **Date:** 2026-08-11 · **Status:** Approved from product-owner specification

## Context

Phase 1 exposes score methodology and primary response evidence. Phase 2 must make those artifacts navigable as a reproducible research workspace and add persistence only for facts that cannot be derived: publication interventions and provider first-observed timestamps.

## Functional Requirements

- FR-1: Research laboratory. The system MUST compose metric, model, prompt, response, entity, citation, graph and recommendation provenance for one research without new LLM calls.
- FR-2: Per-model contribution. The system MUST show observed response-level signals and MUST NOT call them model Visibility scores unless such a scoring contract exists.
- FR-3: Model explorer. Exact raw/structured response, extracted artifacts, region/language, usage, date and prior observations MUST be navigable.
- FR-4: Source intelligence. Sources MUST be grouped by URL/domain/provider/model with citation count and exact v1 contribution; unavailable domain authority MUST be labelled unavailable.
- FR-5: Entity explorer. Entities MUST show aliases, response/provider/model occurrences, sources, neighbours and historical occurrences.
- FR-6: Graph 2.0. Directed nodes/edges MUST link to response evidence when recorded and state when edge evidence is absent.
- FR-7: Publication observations. Publication URL/hash/time and exact first-observed provider/model/time MUST be persisted; missing observations MUST remain NOT_OBSERVED.
- FR-8: Media impact. Observed before/after deltas MUST be separated from causal attribution and forecasts; causality MUST remain unproven without controlled evidence.
- FR-9: Timeline. Research, responses, graph, sources, metric calculation, publication and observation events MUST be ordered by their real timestamps.
- FR-10: Diff. Any two researches MUST compare scores, responses, entities, sources and provider opinion signals using persisted data.
- FR-11: Recommendation 2.0. Trigger evidence, affected models, missing sources, steps, predicted metrics, duration and confidence MUST be shown; predictions MUST be labelled.
- FR-12: Compatibility. Existing endpoints MUST remain backward compatible; new contracts MUST be additive and read-only except publication/observation recording.

## Non-Functional Requirements

- NFR-1: Laboratory reads MUST perform no provider/LLM calls.
- NFR-2: Raw responses MUST be rendered as escaped text and protected by existing auth/RBAC.
- NFR-3: No fake benchmark, authority, source or causal claim is permitted.
- NFR-4: Lists MUST have honest empty states and deterministic ordering.
- NFR-5: PostgreSQL migrations MUST upgrade and downgrade cleanly.

## Acceptance Criteria

### AC-1: Laboratory chain (FR-1, FR-2, FR-3)
Given a completed research, when its laboratory is opened, then every score is connected to participating model responses, exact prompts, raw payloads and extracted artifact IDs.
### AC-2: Source and entity evidence (FR-4, FR-5, FR-6)
Given extracted artifacts, when a source/entity/edge is selected, then recorded provider/model/response relationships are shown and unavailable evidence is explicit.
### AC-3: Publication truth (FR-7, FR-8)
Given a publication and later observations, when impact is read, then publication and first-observed timestamps are exact and deltas are labelled observed, forecast or unproven causality.
### AC-4: Timeline and diff (FR-9, FR-10)
Given two researches, when compared, then actual response/entity/source/model-signal additions/removals and metric deltas are returned in deterministic order.
### AC-5: Recommendation proof (FR-11)
Given a recommendation, when expanded, then its trigger, affected responses/models, missing sources, plan and marked prediction are visible.
### AC-6: Quality gate (FR-12, NFR-1, NFR-2, NFR-3, NFR-4, NFR-5)
Given existing clients, when Phase 2 is deployed, then old contracts pass, migrations reverse, no read invokes an LLM and all automated gates pass.

## Edge Cases

- EC-1: No prior research. Diff/timeline MUST state insufficient history.
- EC-2: Failed response. Explorer MUST retain provider error and raw payload.
- EC-3: Citation without URL. It MUST remain source evidence without invented domain/authority.
- EC-4: Publication never observed. All providers MUST remain NOT_OBSERVED.
- EC-5: Same URL observed repeatedly. Earliest exact observation MUST be retained as first observed.
- EC-6: Graph edge without response metadata. UI MUST state evidence was not recorded.

## API Contracts

```ts
GET /research/{id}/laboratory -> ResearchLaboratory
GET /research/diff?left={id}&right={id} -> ResearchDiff
POST /research-publications -> ResearchPublication
POST /research-publications/{id}/observations -> PublicationObservation
GET /research-publications?entity_id={uuid} -> ResearchPublication[]
```

All new read shapes are additive. Create operations validate real URL/timestamps and never calculate influence at write time.

## Data Models

| Model | Required fields |
|---|---|
| ResearchPublication | id, entity_id, research_id?, url, content_hash, published_at, title, created_at |
| PublicationObservation | id, publication_id, research_id, response_id, provider, model, first_observed_at, evidence_excerpt, created_at |

Existing Research/Response/Extracted*/ResearchScore/Graph* remain the sources for laboratory and diff.

## Out of Scope

- OS-1: No provider-specific index speed is invented without observations.
- OS-2: No causal publication claim is generated from correlation alone.
- OS-3: No new decorative dashboard or benchmark.
- OS-4: No hidden per-model Visibility algorithm is introduced in Scoring 1.0.
