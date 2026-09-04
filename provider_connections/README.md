# Provider Connections

Organization-scoped BYOK connections for external LLM providers.

The UI presents neutral API slots. On save, the service detects a provider from a
unique key prefix, validates the credential against that provider's model endpoint,
encrypts it at rest, and exposes only a masked suffix. Ambiguous key formats require
an explicit provider hint so a credential is never probed against multiple companies.

New connections default to free-only routing and do not allow paid fallback.
Creating, rotating, and revoking a connection is restricted to organization owners
and administrators and recorded in organization activity.

Endpoints:

- `GET /provider-connections`
- `POST /provider-connections`
- `POST /provider-connections/{id}/test`
- `DELETE /provider-connections/{id}`
