# User Guide

The first product workflow is exposed through the Research Wizard. Choose an active prompt,
research template, brand, models, languages and regions. Review validates capabilities and renders
the final prompt without creating data. Run creates the research and blocks until the complete MVP
pipeline has persisted its outputs.

The final report includes the executive summary, six score metrics, trend, benchmark, insights,
rule-based recommendations, graph summary, extracted entities and sources, provider latency, token
usage, cost and execution time. Existing domain APIs remain available for detailed inspection.

Prompt versions are immutable identities (`code`, `version`). Clone creates the next version;
activate makes it the only active version for its code/language; deprecate prevents new wizard runs
from selecting it. Research templates are read-only product presets seeded by migration `0042`.
