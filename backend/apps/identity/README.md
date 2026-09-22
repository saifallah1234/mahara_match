# identity

**Responsibility:** Accounts, roles, permissions, organizations, hierarchy, memberships and verification.

**Logical entity ownership:** users, roles, permissions, user_roles, role_permissions, organizations, organization_members.

**Sources:** DM §4.A; PDF pp. 3–4, 6. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

The Person 1 account/RBAC implementation uses an email-based Django custom user,
custom role/permission tables and JWT. The Person 4 organization/member models are
still required before the shared initial migration can be generated.

The ANETI employment advisor is the system AI agent, not a human user role
(user clarification, 2026-09-20; Q22). Do not implement the source's ANETI_AGENT
account mapping as a human advisor requirement. ANETI organization records remain
a separate concept; the agent's execution authorization must use application services.

## Reserved boundaries

- `api/`: DRF transport, request validation and response representation.
- `services/`: application operations, authorization and business coordination.
- `models/`: Django ORM definitions owned by this domain.

Cross-domain operations use the owning service; do not duplicate entities or mutate
another domain's models directly. Open requirements are tracked in the
[question register](../../../docs/architecture/open_questions.md).
