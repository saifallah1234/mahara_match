# platform

**Responsibility:** Shared notification records and audit history.

**Logical entity ownership:** notifications, audit_logs.

**Sources:** DM §4.E; PDF pp. 4, 6–7. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

This is a narrow supporting domain, not a generic business-logic container. Product rules and state history remain in their owning domains; delivery channels remain unspecified.

## Current backend

Notifications and audit logs have ORM models and trusted append services. Users
read and mark their own notifications; audit reads require `platform.audit.read`.
Audit records identify a user, an agent execution or the system. The initial schema
migration is applied; no public audit write/delete route or delivery channel exists.
