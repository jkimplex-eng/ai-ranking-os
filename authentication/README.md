# Authentication

Independent authentication domain for access JWTs, rotating refresh tokens, revocation,
Argon2id password hashing, session tracking, and token versioning. The
`IdentityProvider` port reserves OAuth2/OpenID Connect integration without coupling the
domain to an external provider.

Refresh tokens are stored only as SHA-256 fingerprints. Reuse of a rotated token revokes
its complete token family. Configure `AUTH_JWT_SECRET`, issuer, audience, and TTL values
through environment settings; the development default must never be used in production.
