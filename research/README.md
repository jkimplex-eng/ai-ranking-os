# Research

The Research domain stores research plans, provider tasks, normalized responses,
and provider-independent intelligence extraction results. After normalization,
`ExtractionService` derives entities, citations, and recommendations and updates
the response processing status to `PROCESSED` or `FAILED`.

Scoring Engine v1 aggregates completed response intelligence into five
0–100 components and one AI Visibility Score. Formula weights are mention 35%,
recommendation 20%, citation 15%, coverage 20%, and confidence 10%. Scores are
stored per research and algorithm version.

`GET /research/{id}/report` assembles the persisted research, latest score,
responses, entities, citations, and recommendations. Reporting performs no
domain calculations and does not mutate pipeline state.

`GET /research/compare?left={id}&right={id}` compares two scored reports.
It returns `right - left` metric deltas plus new and disappeared entities and
recommendations without changing either research.

`GET /research/history?entity_id={uuid}` returns newest-first, paginated history
for a tracked entity. Each row includes its latest score, model and processed
response counts; aggregate statistics cover the full matching history.
