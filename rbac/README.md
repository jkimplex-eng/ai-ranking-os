# RBAC

Independent role and permission domain. Permissions use `resource/action/scope`; roles may
inherit multiple parents. The service rejects inheritance cycles and exposes the
`AuthorizationProvider` port. User assignments store opaque platform user IDs and do not
import Authentication internals. System role seeding is intentionally deployment-managed.
