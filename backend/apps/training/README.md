# training

**Future responsibility:** Training catalogue, scheduled sessions, enrollment and recommendations.

**Logical entity ownership:** training_programs, training_skills, training_sessions, training_enrollments, training_recommendations.

**Sources:** DM §4.D; PDF pp. 3, 5–6. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Reference identity providers and canonical skills. Candidate academic education and earned certifications remain candidate-owned; certificate issuance and pricing rules are unresolved.

## Reserved boundaries

- `api/`: future DRF transport, request validation and response representation.
- `services/`: application operations, authorization and business coordination.
- `models/`: future Django ORM definitions owned by this domain.

These directories contain no implementations. No Django app has been initialized.
Cross-domain operations use the owning service; do not duplicate entities or mutate
another domain's models directly. Open requirements are tracked in the
[question register](../../../docs/architecture/open_questions.md).
