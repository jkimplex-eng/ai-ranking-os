# Closed Beta Administration

Administration of beta access states, per-user limits and single-use invitations. Existing
Authentication users and RBAC roles are accessed through ports; invitation secrets are stored
only as SHA-256 digests. Every administrative mutation and invitation acceptance is written to
the immutable platform Audit Log.
