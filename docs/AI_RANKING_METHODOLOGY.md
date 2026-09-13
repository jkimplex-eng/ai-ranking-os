# AI Ranking Methodology 1.0

## Production score

All component scores are normalized to `[0, 100]` and bounded after calculation.

| Metric | Exact formula | Weight in Visibility | Primary inputs |
|---|---|---:|---|
| Mention | `responses mentioning target / all responses × 100` | 35% | Response content and extracted entity names/canonical names/aliases |
| Recommendation | `responses with ≥1 extracted recommendation / all responses × 100` | 20% | ExtractedRecommendation grouped by Response |
| Citation | `extracted citations / (all responses × 3) × 100` | 15% | ExtractedCitation rows; v1 caps contribution at three citations per response |
| Coverage | `unique processed (provider, model) / expected research tasks × 100` | 20% | Processed Responses and Research.total_tasks |
| Confidence | `processing success × 70% + mean entity confidence × 30%` | 10% | Response processing status and ExtractedEntity.confidence; no entities uses 50% prior |
| AI Visibility | `Mention×.35 + Recommendation×.20 + Citation×.15 + Coverage×.20 + Confidence×.10` | 100% | Five component scores above |

Version is stored on each `ResearchScore`. Recalculation of version 1.0 updates the same versioned record rather than silently changing the algorithm.

## Examples

For two responses, one target mention, one response with a recommendation, three citations, two unique processed models, two expected tasks and confidence 94:

- Mention = `1/2×100 = 50`.
- Recommendation = `1/2×100 = 50`.
- Citation = `3/(2×3)×100 = 50`.
- Coverage = `2/2×100 = 100`.
- Visibility = `50×.35 + 50×.20 + 50×.15 + 100×.20 + 94×.10 = 64.4`.

## Why a metric changes

- Mention changes only when the ratio of responses containing the target changes.
- Recommendation changes only when the ratio of responses with extracted recommendations changes.
- Citation changes with extracted citation count or response count (the denominator).
- Coverage changes with unique successful provider/model pairs or expected task count.
- Confidence changes with processing success and extracted entity confidence.
- Visibility changes as the weighted result of those five changes.

Trend deltas are observations, not causal attribution. A publication must not be claimed as the cause without a recorded intervention and matched before/after observations.

## Metrics not in production Scoring 1.0

- **Authority:** an experimental AI Visibility pipeline contains citation-authority inputs, but ResearchScore v1.0 does not. It is displayed as `NOT_CALCULATED_IN_SCORING_V1`.
- **Benchmark:** a comparative rank/percentile produced by the Benchmark Engine. It requires at least two entities and does not contribute to Visibility 1.0.
- **Knowledge Graph Score:** not defined in the production scoring contract. Node/edge counts and confidence are evidence, not a hidden score.

## Evidence chain

`Research → ResearchTask → Response(prompt, raw response, usage) → extracted entities/citations/recommendations → ResearchScore → Recommendation rule/template → deterministic Simulation`.

Every final report exposes this chain under the additive `explainability` property. Unsupported or historically absent evidence is reported as unavailable and never reconstructed.
