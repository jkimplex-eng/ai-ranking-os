# First Real Product

The `product` module is an orchestration layer over public platform services. It owns only the
versioned prompt library and research-template catalog. Research execution, normalization,
extraction, scoring, graph, recommendations, analytics, insights, benchmark and trend calculations
remain in their existing domains.

Use `POST /research/wizard/review` to validate a selection and render its prompt, then
`POST /research/wizard/run` to execute the complete pipeline. The result contains the research and
the final report; it remains available through `GET /research/{id}/final-report`.
