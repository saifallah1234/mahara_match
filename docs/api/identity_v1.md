# Identity API v1 contract

Status: implemented for the Person 1 identity/RBAC slice. Database migrations and
PostgreSQL integration remain gated on the Person 4 `Organization` and
`OrganizationMember` models in the shared identity app.

## Authentication and transport

- Base path: `/api/v1/`.
- Authentication: JWT access tokens last 30 minutes; rotating refresh tokens last
  30 days and are blacklisted after rotation or logout.
- Only `ACTIVE` users may obtain or refresh tokens. Tokens contain identity, not
  cached roles or permissions.
- Lists use `page` and `page_size`, defaulting to 20 and capped at 100.
- Errors use `{"error":{"code":"...","message":"...","details":{...}}}`.
- OpenAPI is served at `/api/v1/schema/` and Swagger UI at `/api/v1/docs/`.

## Identity resources

| Resource | Methods | Authority |
| --- | --- | --- |
| `auth/token`, `auth/token/refresh`, `auth/token/verify` | POST | Public token operations |
| `auth/logout` | POST | Active authenticated user |
| `users/me` | GET, PUT, PATCH | Own first name, last name and phone |
| `users` | GET, POST | `identity.user.manage` |
| `users/{id}` | GET, PUT, PATCH | `identity.user.manage` |
| `roles` | GET | `identity.rbac.manage` |
| `roles/{id}` | GET, PATCH | Name and description only; `identity.rbac.manage` |
| `permissions` | GET, POST | `identity.rbac.manage` |
| `permissions/{id}` | GET | `identity.rbac.manage` |
| `user-roles` | GET, POST | `identity.rbac.manage` |
| `user-roles/{id}` | GET, DELETE | `identity.rbac.manage` |
| `role-permissions` | GET, POST | `identity.rbac.manage` |
| `role-permissions/{id}` | GET, DELETE | `identity.rbac.manage` |

Users, roles and permissions have no public DELETE operation. User status,
credentials, verification timestamps, technical flags, identifiers and timestamps
are protected. A new administratively created user starts in `PENDING`.

## Application-service contract

Callers outside the HTTP adapter use the owning services, never direct model writes:

- `identity.services.users`: list/get/create users and update permitted profile fields.
- `identity.services.access`: `effective_permission_codes`, `has_permission`, and
  `require_permission`, optionally scoped to an organization UUID.
- `identity.services.user_roles`: list/get/assign/remove role assignments.
- `identity.services.role_permissions`: list/get/grant/revoke permission grants.
- `identity.services.roles` and `identity.services.permissions`: governance reads and
  permitted configuration writes.

Global `CANDIDATE` and `ADMIN` assignments have no organization. `RECRUITER`,
`TRAINING_MANAGER` and `MINISTRY_MANAGER` assignments require a compatible
organization and an active membership. Baseline grants cannot be removed.
