# Research Intelligence 1.1

AI Ranking OS now evaluates a brand across a reproducible demand sample rather than a
single branded prompt.

## Research contract

The product wizard builds eight query clusters: brand awareness, category discovery,
recommendation, problem/solution, comparison, trust, commercial intent, and independent
evidence. Every selected runtime-ready model receives every query. The query catalog and
its deterministic identifiers are stored in `Research.metadata`.

Existing `POST /research/{id}/run` clients remain compatible. The optional `queries` field
extends `ResearchRunRequest`; omitted queries preserve the previous single-query behavior.

## Scoring 1.1

Visibility remains the weighted combination of Mention, Recommendation, Citation,
Coverage, and Confidence. Coverage now measures processed responses against the complete
query-model task matrix. Confidence includes a sample-sufficiency component and cannot
reach its maximum from a single response.

A component value of 100 means saturation only inside the saved sample. It is never a
claim of universal visibility across all AI systems.

## Pattern analysis

The final report contains:

- the complete query-response matrix;
- queries where the brand was absent;
- entities named instead of the brand;
- citation domains repeated across responses;
- sample size, failures, providers, and runtime models.

## GEO opportunity plan

Recommendations use observed sources first. When no source is observed, the report names
an honest resource category rather than inventing a domain. Every action includes evidence,
deliverable, metric, expected range, confidence, effort, duration, verification, and a
causality limitation.

Publication impact is a hypothesis until an identical follow-up research confirms a change.
