# Recommendation Impact Simulator

Simulation model `1.0` estimates every recommendation independently using its
rule threshold and the fixed Scoring v1 metric weights. It assumes 75% expected
target realization and exposes a 50%/75%/100% Visibility range as
`confidence_min`, `confidence_expected`, and `confidence_max`.

The simulator core depends on `ResearchScoreSource`, not Research persistence.
It uses no LLM calls and produces reproducible results for the same score,
recommendation set, rules, templates, and model version.
