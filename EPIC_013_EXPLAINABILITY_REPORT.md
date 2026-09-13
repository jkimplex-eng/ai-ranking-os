# EPIC-013 — Explainability Implementation Report

## Outcome

AI Ranking OS now exposes an evidence chain from each production score to Research, exact prompts, full raw/normalized provider responses, extracted entities/citations/recommendations and deterministic recommendation forecasts. No new top-level UI section, LLM call, database table or breaking API change was introduced.

## Task mapping

| Task | Implementation |
|---|---|
| 1301 Methodology | Exact Scoring 1.0 formulas, weights, normalization, examples and change causes in `docs/AI_RANKING_METHODOLOGY.md`; machine-readable metric explanations in final report |
| 1302 Prompt Observatory | Existing report embeds a prompt catalog with deterministic UUID, exact text, language/region, provider/model, response ID and timestamp |
| 1303 Response Explorer | Existing report exposes full persisted raw and normalized payloads, usage, cost, latency, errors and extracted artifact IDs without truncation |
| 1304 Citation Analyzer | Citation evidence is grouped by response/provider/model and real parsed domain; zero citations are explicit |
| 1305 Knowledge Sources | Existing report lists actual sources/domains or an evidence-based empty state; no new navigation section under feature freeze |
| 1306 Graph Explorer | Existing Knowledge Graph renders real nodes/directed edges, search/type filters, confidence and node relationship details |
| 1307 Provider Matrix | Versioned research register in `docs/AI_PROVIDER_MEDIA_RESEARCH.md`; only documented capabilities are asserted, all others are `unknown` |
| 1308 Media Matrix | No unsupported High/Medium/Low claims; matrix records `unknown` pending reproducible experiments and defines their protocol |
| 1309 Crawl Timeline | Defines publication vs first-observed semantics and `NOT_OBSERVED`; no inferred crawl dates or unused persistence model |
| 1310 Recommendation Explainability | Trigger metric/value, deterministic rule, template steps and supporting response/citation counts are linked in report |
| 1311 Influence Attribution | Observed trend delta is labelled observational; causal claims are prohibited without matched intervention evidence |
| 1312 Simulator | Reuses existing deterministic RecommendationSimulation and visibly labels output `ПРОГНОЗ`, version/range/confidence/time |
| 1313 Executive Explainability | Dashboard “Почему мой рейтинг такой?” opens the existing report evidence chain |

## Public contract

`GET /research/{id}/final-report` has one additive optional property: `explainability`. Existing properties and endpoints remain unchanged. The bundle contains methodology version, metric formulas/inputs, prompts, full response evidence, citations and unsupported metrics.

Authority and Knowledge Graph Score are explicitly `NOT_CALCULATED_IN_SCORING_V1`; Benchmark remains unavailable for fewer than two entities. They are not substituted with proxy numbers.

## Verification

- Implementation spec strict validation: 100/100.
- Ruff: PASS.
- Pytest: 287 PASS.
- Compileall: PASS.
- TypeScript: PASS.
- ESLint: PASS.
- Frontend build: PASS.
- Playwright application suite: 4 PASS.
- No schema migration required: all primary evidence was already persisted.

## Known limitations

- Provider training/index composition is proprietary or undocumented for many providers and remains `unknown`.
- Media influence needs controlled observations; the system does not present speculative domain influence as fact.
- Crawl timelines have no rows until an exact URL/content is observed in an actual response. Research timestamps are never used as crawl timestamps.
- Historical responses that did not record a prompt/raw payload cannot be reconstructed.
