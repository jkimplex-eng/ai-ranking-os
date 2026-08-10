# Product Analytics

Internal analytics for how AI Ranking OS itself is used. The module owns a unified event
stream, sessions and cached materialized reports. It does not import Research or AI Visibility
domains and does not rely on third-party analytics services.

Events are recorded through `ProductAnalyticsService` by HTTP instrumentation or the bounded
batch endpoint. Dashboard aggregates are cached for five minutes and can be refreshed through
the batch-oriented refresh endpoint. Exports support JSON, CSV and XLSX.
