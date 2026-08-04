# Recommendation Engine

Recommendation Engine v1 converts persisted score snapshots into concrete,
prioritized actions using versioned database rules. The engine core depends on
the `ResearchScoreSource` protocol; `SqlAlchemyResearchScoreAdapter` is the only
integration layer aware of Research persistence.

Default v1 rules cover low Mention, Citation, Recommendation, and Coverage
scores. Every generation creates an immutable execution record and a set of
recommendations containing type, priority, explanation, metric, and expected
effect.

The `templates` submodule stores versioned, reusable action plans. Generation
pins every matching recommendation to a template row, while
`GET /research/{id}/action-plan` assembles the persisted recommendation and
template into a read-only execution plan.

The `simulation` submodule closes the first recommendation loop with a
deterministic, versioned impact forecast. It uses the score-source port and
persists one simulation per recommendation without depending on Research
implementation details.
