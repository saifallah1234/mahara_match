# Identity API v1 contract

Status: implemented for the Person 1 identity/RBAC slice. Database migrations and
PostgreSQL integration remain gated on the Person 4 `Organization` and
`OrganizationMember` models in the shared identity app.

## Authentication and transport

- Base path: `/api/v1/`.
- Authentication: JWT access tokens last 30 minutes. Rotating refresh tokens last
  30 days, are stored only in the `mahara_refresh` HttpOnly cookie and are
  blacklisted after rotation, logout or an account-status change.
- Only `ACTIVE` users may obtain or refresh tokens. Tokens contain identity, not
  cached roles or permissions.
- Browser registration uses `POST auth/register` after CSRF bootstrap. It accepts
  email, password, first_name, last_name, optional phone, and `account_type`
  (`CANDIDATE`, `RECRUITER`, or `TRAINING_MANAGER`). Organization applicants also
  provide `organization_name` and `matricule_fiscal`. It returns `{user_id,status}`.
- Lists use `page` and `page_size`, defaulting to 20 and capped at 100.
- Errors use `{"error":{"code":"...","message":"...","details":{...}}}`.
- OpenAPI is served at `/api/v1/schema/` and Swagger UI at `/api/v1/docs/`.

The browser transport is same-origin. `GET /api/v1/auth/csrf/` issues Django's
readable CSRF cookie. Login, refresh and logout require its value in Django's
`X-CSRFToken` header. The refresh cookie is HttpOnly, `SameSite=Lax`, scoped to
`/api/v1/auth/`, secure outside debug mode and never returned in JSON. Login and
refresh return only an access token. Refresh rotates the cookie; logout blacklists
valid refresh credentials and always clears the cookie. Already issued access
tokens remain valid until their 30-minute expiry unless the account becomes
inactive. Token verification also checks the current account status.

## Identity resources

| Resource | Methods | Authority |
| --- | --- | --- |
| `auth/csrf` | GET | Public CSRF-cookie bootstrap |
| `auth/register` | POST | Public candidate registration or pending organization request; CSRF required |
| `auth/token`, `auth/token/refresh`, `auth/token/verify` | POST | Public token operations; login and refresh require CSRF |
| `auth/logout` | POST | Active authenticated user |
| `users/me` | GET, PUT, PATCH | Own first name, last name and phone |
| `onboarding-requests` | GET | `identity.rbac.manage`; paginated review queue |
| `onboarding-requests/{id}/approve` | POST | `identity.rbac.manage`; `{organization_id}` |
| `onboarding-requests/{id}/reject` | POST | `identity.rbac.manage` |
| `users` | GET, POST | `identity.user.manage` |
| `users/{id}` | GET, PUT, PATCH | `identity.user.manage` |
| `users/{id}/status` | POST | Set one declared account status; `identity.user.manage` |
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
are protected from ordinary profile writes. A new administratively created user
starts in `PENDING`. The privileged status action accepts only `PENDING`, `ACTIVE`,
`SUSPENDED` and `DISABLED`. No narrower transition matrix or email-verification
side effect is encoded because neither is approved. Status assignment is idempotent.
Every actual status change blacklists all outstanding refresh credentials. Existing
access credentials stop authenticating as soon as the account is not `ACTIVE`.

`GET users/me` is available to every active authenticated user, including one
with no roles. It retains `role_assignments` and adds `workspaces`, each with a
`role_code` and either a null organization or its id, legal name, type and
verification status. Scoped workspaces require a current membership in a
verified, non-deleted organization. Domain permissions use the same eligibility.

Candidate registration atomically creates an active account, global candidate
role and private profile; it does not mark the email verified. Recruiter and
training-manager registration creates a pending account and review request.
An administrator matches or creates and verifies an organization, then approves
against its ID. Approval checks the request's matricule fiscal and organization
type, creates membership and scoped role, and activates the account atomically.
Rejected requests remain pending accounts. Ministry and admin accounts are
provisioned only through privileged identity operations.

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
