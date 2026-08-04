# Provider Credentials

Credential lookup occurs on every provider operation, so rotation does not
require an application restart. Precedence is:

1. in-process hot override;
2. environment variable;
3. Docker secret under `/run/secrets`;
4. Kubernetes-mounted secret under `/var/run/secrets/ai-ranking-os`;
5. injected Vault resolver.

Required names are listed in `.env.example`. Never commit live values. Set
`PROVIDER_MOCK_MODE=true` for tests and local development. For live smoke tests,
set it to `false`, configure only the target provider keys, and restrict the
test to low token limits.

The Vault-ready interface accepts a resolver callback. Rotation controllers can
call `CredentialManager.set()` for an immediate override and `clear()` to
resume mounted/environment lookup.

Authentication failures are normalized as `authentication`; missing credentials
as `configuration`. Logs and metrics must never contain credential values.
