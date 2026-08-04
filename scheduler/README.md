# Scheduled Research

`SchedulerEngine` manages recurring Research launches without importing the Research
domain. It calls the public `ResearchLauncher` port; `research_adapter.py` clones a
configured Research template and invokes the existing run workflow.

Schedules support `HOURLY`, `DAILY`, `WEEKLY`, `MONTHLY`, and standard five-field
`CRON` expressions. Cron fields accept wildcards, lists, ranges, and steps. All
calculations use UTC.

Concurrency is protected by `FOR UPDATE SKIP LOCKED` and a PostgreSQL partial unique
index allowing only one `RUNNING` execution per schedule. Retry attempts use bounded
exponential backoff and each attempt is stored in `schedule_history`.

- `POST /schedules`
- `GET /schedules`
- `PATCH /schedules/{id}`
- `DELETE /schedules/{id}`
- `POST /schedules/run`

