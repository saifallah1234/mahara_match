# recruitment

**Future responsibility:** Offers, applications and recruitment follow-up.

**Logical entity ownership:** job_offers, offer_skills, applications, application_status_history, interviews.

**Sources:** DM §4.C; PDF pp. 3, 5–6, 10. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Reference identity organizations, candidate CV versions and taxonomy. Do not own organization copies, import histories or matching algorithms. External application tracking is not supported by the model's Easy_apply description.

## Reserved boundaries

- `api/`: future DRF transport, request validation and response representation.
- `services/`: application operations, authorization and business coordination.
- `models/`: future Django ORM definitions owned by this domain.

These directories contain no implementations. No Django app has been initialized.
Cross-domain operations use the owning service; do not duplicate entities or mutate
another domain's models directly. Open requirements are tracked in the
[question register](../../../docs/architecture/open_questions.md).
