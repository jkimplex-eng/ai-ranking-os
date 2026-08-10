# TASK-1118 — Organization Workspace

## Delivered

- Organization profile with branding metadata, industry, country, timezone,
  settings, and configurable limits.
- OWNER, ADMIN, MEMBER, and VIEWER memberships with protected owner role.
- Organization switching and one default organization per user.
- Expiring, hashed invitations with accept and revoke lifecycle.
- Member management, role changes, project links, member/project limit enforcement,
  and append-only activity history.
- Responsive Web UI for organization switching, team invitations, limits, and activity.
- Reversible migration `0071_add_organization_workspace`.

## Compatibility

Personal Workspace and project APIs remain unchanged. Organization collaboration
is an additive bounded context and project association uses a dedicated link table.

## API

Organization CRUD/profile, switch, members, invitations, projects, and activity
are exposed under `/organizations` and documented in OpenAPI.
