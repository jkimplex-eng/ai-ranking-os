# EPIC-013 Phase 3 — Product Experience & Explainability

## Result

The user now selects concrete active models from the production registry, chooses research scope,
research profile and execution mode, and sees evidence-based explanations and simulations in the
report. Existing API clients remain compatible because the new wizard fields have defaults.

## Delivered

- Eight-step research wizard with a real Registry-backed model catalog.
- Multi-select, select-all, clear and browser-local user presets.
- Research scopes: all, selected, Russian, commercial, free, consensus and compare. Registry
  attributes drive all/free/Russian/commercial filtering; consensus/compare retain the explicitly
  selected set because no separate execution contract currently exists.
- Research profiles: GEO, ecommerce, medical, beauty, enterprise and universal.
- Persisted scope, profile, routing mode and exact selected provider/model pairs in Research metadata.
- Evidence explanations for mentions, recommendations, citations and coverage, separated into
  positive and deficit model signals.
- Explicit unknown-cause label where a model did not state why it omitted a recommendation.
- Action simulator over persisted RecommendationSimulation outputs with forecast labelling.
- Model, entity, source, provenance and timeline sections from Phase 2 integrated into the report.
- Graph node/edge explorer exposes stored edge properties or explicitly says evidence was not saved.
- Primary application navigation and research terminology translated into Russian.
- Honest empty states for missing registry models, extraction, graph, publications and simulations.

## Validation

- Ruff: PASS.
- Pytest: PASS, 291 tests.
- Compileall: PASS.
- OpenAPI: PASS, 232 paths; additive WizardRequest fields are published.
- TypeScript: PASS.
- ESLint: PASS.
- Frontend build: PASS.
- Playwright: PASS, 4 active tests; 2 production-only tests remain environment-gated.

## Non-fabrication decisions and open blockers

- No per-model Visibility score or model weighting is displayed because Scoring v1.0 has no such
  contract.
- No Domain Authority is fabricated. It remains unavailable until a measured authority provider is
  integrated.
- Missing recommendations are described as observed response omissions. The product does not claim
  missing media, reviews or research unless response/source evidence proves that claim.
- The existing graph is a real interactive directed SVG; relationships are sparse because the
  production ResearchEntityProvider currently emits no relationships. Inventing edges is prohibited.
- Automatic website crawling, product-matrix extraction and product-level competitor discovery are
  not present in the platform. The existing competitor screen continues to show only persisted
  workspace competitors. BLOCK 6 therefore remains a real backend capability gap, not a UI task.
- AI index speed, preferred media and platform coverage require longitudinal publication observations.
  Until sufficient observations exist, the system reports insufficient data rather than static claims.
- Profile-specific prompt and scoring-weight versions are persisted but Scoring v1.0 remains unchanged.
  Applying different weights requires a new versioned scoring methodology and regression dataset;
  silently changing v1.0 would break reproducibility.

## Changed contracts

`WizardRequest` adds optional `research_scope` and `research_profile`. Both have backward-compatible
defaults. The final report laboratory provenance adds `metric_explanations` without changing existing
fields.
