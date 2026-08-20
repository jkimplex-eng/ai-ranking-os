# Competitor Intelligence

The module aggregates competitor visibility and publication evidence from completed project
researches. It owns daily snapshots and source observations, while competitor CRUD remains in the
public Workspace API and recurring execution remains in Scheduler/Project Monitoring.

`observed_visibility_score` is a module-specific observation index, not the primary AI Visibility
score. Publication significance measures recurrence, provider coverage and recommendation
co-occurrence. It must never be presented as proof of causality or knowledge of provider ranking
algorithms.

API:

- `GET /competitor-intelligence/projects/{project_id}`
- `POST /competitor-intelligence/projects/{project_id}/refresh`
- `PUT /competitor-intelligence/projects/{project_id}/daily-monitoring`

