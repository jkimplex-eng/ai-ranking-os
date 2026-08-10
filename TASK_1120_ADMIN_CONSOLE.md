# TASK-1120 — Admin Console

The Admin Console provides one operational UI for Users, Organizations,
Research, Reports, Providers, Jobs, Feedback, Product Analytics, Audit, Health,
and Settings. It is an orchestration layer over existing authenticated public
APIs and does not duplicate domain models or administrative business logic.

Access is enforced by existing backend authorization policies. Health and audit
data remain read-only; mutating workflows continue through their owning domain
screens and services.
