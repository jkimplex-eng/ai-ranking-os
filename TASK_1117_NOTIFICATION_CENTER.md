# TASK-1117 — Notification Center

## Delivered

- Standard events for completed/failed research, ready reports, organization
  invitations, role changes, processed feedback, and system notices.
- Backward-compatible operational events for changes, budgets, providers, and executions.
- In-app delivery plus provider-neutral Email, Telegram, and Webhook outbox channels.
- User-scoped read/unread state, read timestamps, archive, categories, priorities,
  filters, counters, and pagination.
- Responsive notification inbox in the Web UI.
- Reversible Alembic migration `0070_expand_notification_center`.

## API additions

- `GET /notifications/summary`
- `POST /notifications/{notification_id}/archive`
- Extended `GET /notifications` filters and pagination.

## Compatibility

Existing notification creation, listing, and mark-read contracts remain valid.
The public `NotificationPort` continues to isolate producers from delivery details.

## Verification

TASK-specific unit/API, Ruff, TypeScript, frontend build, Playwright, full Pytest,
OpenAPI, PostgreSQL migration, Docker, and GitHub Actions results are recorded at
the completion gate.
