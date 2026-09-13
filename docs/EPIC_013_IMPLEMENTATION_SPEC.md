# EPIC-013 — AI Ranking Methodology & Explainability

**Author:** Codex · **Date:** 2026-08-11 · **Status:** Approved (derived from user P0 specification) · **Reviewers:** CTO/Product owner

## Context

The platform persists prompts, raw and normalized responses, extracted entities/citations/recommendations, scores, graph snapshots and deterministic simulations, but these artifacts are composed inconsistently. Users can see a score without always being able to trace it to the inputs and formula. EPIC-013 creates one evidence chain without replacing engines or inventing evidence.

Feature freeze remains binding. Explainability is embedded in existing Dashboard, Report and Knowledge Graph screens. A public contract may only be extended additively when an existing persisted artifact cannot otherwise be exposed.

## Functional requirements

- FR-1: Metric calculation.
Every displayed metric MUST expose formula, version, normalized range, weights, actual inputs and computed result.
- FR-2: Visibility composition.
Visibility MUST trace to Mention, Recommendation, Citation, Coverage and Confidence using Scoring v1.0 weights 35/20/15/20/10.
- FR-3: Unsupported scores.
Authority, Benchmark and Knowledge Graph Score MUST be labelled unavailable when the active production scoring contract does not calculate them; they MUST NOT be fabricated.
- FR-4: Primary evidence.
Every research MUST expose the exact prompt and full raw/normalized response already persisted, with provider/model/time/tokens/cost/latency and extracted artifacts.
- FR-5: Citation evidence.
Citation evidence MUST aggregate actual citations by response, provider, source and domain; zero citations MUST have an evidence-based empty state.
- FR-6: Graph evidence.
The existing graph screen MUST render real directed edges and show edge confidence, type, source evidence/properties and connected nodes.
- FR-7: Research knowledge base.
Provider and media research MUST be a versioned, cited project knowledge base; unknown attributes MUST remain `unknown`.
- FR-8: Crawl observations.
Crawl observations MUST distinguish publication time from first observed time per provider and MUST NOT infer crawl time from research time.
- FR-9: Recommendation evidence.
Every recommendation MUST trace to its triggering metric, threshold/rule version, relevant response/citation evidence, action template and deterministic simulation where available.
- FR-10: Attribution honesty.
Attribution MUST distinguish observed deltas from predictions. Causal claims MUST NOT be emitted without an explicit matched intervention and before/after evidence.
- FR-11: Simulator evidence.
Simulator outputs MUST reuse deterministic RecommendationSimulation data and show model version, assumptions, range and confidence; unavailable simulations MUST be labelled unavailable.
- FR-12: Explainability entry point.
Dashboard and Report MUST provide a single explainability entry point reaching prompts, responses, entities, sources, formulas and recommendation evidence.
- FR-13: Compatibility.
Existing public response fields MUST remain backward compatible.

## Non-functional requirements

- **NFR-1:** Explainability composition MUST be read-only and add no LLM calls.
- **NFR-2:** Existing report requests SHOULD remain below 500 ms excluding database/network variance; no N+1 per response.
- **NFR-3:** Raw responses MUST inherit existing authentication/RBAC and MUST be escaped as text in the browser.
- **NFR-4:** All factual statements MUST link to persisted IDs or cited external research; predictions MUST carry a visible `ПРОГНОЗ` label.
- **NFR-5:** UI MUST support keyboard navigation, semantic headings and honest empty/error states.

## Acceptance criteria

### AC-1: Metric proof (FR-1, FR-2, FR-3)
Given a completed research, when calculation details open, then every production score shows formula, inputs, normalized value and algorithm version, while unsupported scores say they are not calculated.
### AC-2: Primary evidence (FR-4)
Given persisted responses, when evidence opens, then exact prompt/raw response, provider/model, usage, latency, cost and extraction artifacts are visible without truncation.
### AC-3: Citation proof (FR-5)
Given zero citations, when the citation panel opens, then it reports zero per provider and states that no external evidence was extracted; given citations, domains and sources are counted from citation records.
### AC-4: Graph proof (FR-6)
Given graph edges, when a node/edge is selected, then direction, type, confidence and properties/evidence are visible; with zero edges an explicit reason is shown.
### AC-5: Research provenance (FR-7, FR-8)
Given provider/media/crawl knowledge, when displayed, then every non-unknown claim has a citation or experiment reference and observed timestamps are not inferred.
### AC-6: Recommendation proof (FR-9, FR-10, FR-11)
Given a recommendation, when expanded, then trigger evidence, action plan and marked deterministic prediction are shown; missing simulation is not replaced with a number.
### AC-7: Executive entry point (FR-12)
Given Dashboard or Report, when the user activates “Почему мой рейтинг такой?”, then the complete evidence chain is reachable without a new top-level navigation section.
### AC-8: Compatibility gate (FR-13, NFR-1, NFR-2, NFR-3, NFR-4, NFR-5)
Given an existing client and completed research, when explainability is read, then existing tests and OpenAPI contracts remain green and no LLM call occurs.

## Edge cases

- EC-1: No responses.
Show scoring unavailable, not zero evidence.
- EC-2: Failed response.
Show error type/message and preserve raw provider payload.
- EC-3: Citation without URL.
Group under recorded source/title, never invent a domain.
- EC-4: Missing historical payload.
State that the artifact was not recorded.
- EC-5: Insufficient benchmark.
One entity produces an unavailable benchmark.
- EC-6: Graph evidence absent.
Label edge as extracted relation without source metadata.
- EC-7: No intervention.
Attribution is correlation/forecast only.
- EC-8: Provider changes.
Knowledge records remain versioned with checked dates.

## API contracts

Existing contracts remain authoritative: `GET /research/{id}/final-report`, `GET /research/{id}/report`, `GET /graph`, `GET /research/{id}/action-plan`, `GET /research/{id}/simulation`. Any explainability extension MUST be additive and optional:

```ts
interface ExplainabilityBundle {
  methodology_version: string;
  metrics: Record<string, MetricExplanation>;
  prompts: PromptEvidence[];
  responses: ResponseEvidence[];
  citations: CitationEvidence[];
  unsupported_metrics: string[];
}
```

## Data models

No new model is required for prompts/responses/citations because `Response` and extracted artifacts already persist the required data. Provider/media research is documentation-backed static knowledge, not runtime truth. Crawl observations MAY use existing research/citation timestamps until a real observation table is explicitly approved; inferred timestamps are forbidden.

| Existing model | Evidence used |
|---|---|
| Research/ResearchTask | target, status, counts, timestamps, provider/model plan |
| Response | exact prompt, raw/normalized response, usage, cost, latency, errors |
| ExtractedEntity/Citation/Recommendation | primary extraction evidence and confidence |
| ResearchScore | production metric values, version and calculated time |
| GraphSnapshot/Node/Edge | immutable graph and relationship evidence |
| Recommendation/Template/Simulation | rule trigger, steps and explicitly predicted effect |

## Out of scope

- OS-1: Product expansion.
New top-level UI sections, autonomous publishing, new LLM analysis and unverified causal inference.
- OS-2: Provider calls.
Calling provider APIs merely to populate explainability.
- OS-3: Scoring contract changes.
Treating Authority or Knowledge Graph Score as production metrics before a separately approved scoring-version change.
- OS-4: Unverifiable claims.
Claiming proprietary provider crawl/index behaviour without a public source or reproducible experiment.
