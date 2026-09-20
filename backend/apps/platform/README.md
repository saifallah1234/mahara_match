# platform

**Future responsibility:** Shared notification records and audit history.

**Logical entity ownership:** notifications, audit_logs.

**Sources:** DM §4.E; PDF pp. 4, 6–7. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

This is a narrow supporting domain, not a generic business-logic container. Product rules and state history remain in their owning domains; delivery channels remain unspecified.

## Reserved boundaries

- `api/`: future DRF transport, request validation and response representation.
- `services/`: application operations, authorization and business coordination.
- `models/`: future Django ORM definitions owned by this domain.

These directories contain no implementations. No Django app has been initialized.
Cross-domain operations use the owning service; do not duplicate entities or mutate
another domain's models directly. Open requirements are tracked in the
[question register](../../../docs/architecture/open_questions.md).
