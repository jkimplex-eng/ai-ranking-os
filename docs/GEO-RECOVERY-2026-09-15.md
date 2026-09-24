# GEO recovery — 2026-09-15

The GEO screen displayed missing data when organization-dependent API calls failed.
The affected account had no organization membership; research 69 existed without an
organization. Wordstat, learning and automation therefore failed with an unhandled
`ValueError` in `default_organization`.

## Changes

- Provision an isolated personal organization for an active account on first use.
  Lock the account row and recheck memberships to serialize concurrent requests.
  Existing memberships and other organizations are preserved.
- Distinguish API failures from empty data on the GEO screen; allow retry, prevent
  duplicate monitoring creation while its dashboard is unavailable, and ignore stale
  responses after changing the selected research.
- Populate the selected brand, remove the unrelated default category, and align the
  Wordstat controls. Summary cards now represent observed sources, active monitoring
  plans and YandexGPT observations for the selected brand.
- Preserve daily control questions when the template changes. Weekly questions adapt.
- Wait up to 60 seconds for an occupied execution agent, releasing the transaction
  before waiting. Previously, transient contention immediately failed research tasks.

## Validation

- 20 tests: organization provisioning/isolation, provider connections, Wordstat and
  Alice learning/automation.
- 13 tests: bounded queue waiting, execution lifecycle and research domain. These
  require `DATABASE_URL=sqlite:///:memory:` locally for the application lifespan;
  the default local PostgreSQL credentials are not usable.
- Playwright GEO failure/retry scenario passed; TypeScript and production build passed.
- Real production HTTP calls in the affected user's session returned 200 for Wordstat
  status/latest, learning dashboard, automation dashboard and research 69 final report.
- Wordstat returned 14 phrases for `GEO продвижение`; 20 existing YandexGPT observations
  were imported from research 69 into its owner's personal workspace.

## Deployment

Backend, frontend, worker and nginx updated on the existing VPS. Previous backend
and frontend images retained as `ai-ranking-os-rollback:geo-20260915` and
`ai-ranking-os-frontend-rollback:geo-20260915`.
Research 69 was linked only to its verified creator's personal workspace (7).
A second generic product execution agent supports simultaneous monitoring and manual
research. No other organization memberships or provider credentials were changed.

Live verification research: 80. The earlier diagnostic run 78 is preserved with its
original queue-contention failure for traceability.
