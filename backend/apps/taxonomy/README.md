# taxonomy

**Future responsibility:** Shared canonical references reused across business domains.

**Logical entity ownership:** skills, skill_aliases, languages, education_levels.

**Sources:** DM §§3.1, 4.B; PDF pp. 4, 9. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Candidate, offer and training associations stay with those domains. Occupation taxonomy and reference scales are unresolved.

## Reserved boundaries

- `api/`: future DRF transport, request validation and response representation.
- `services/`: application operations, authorization and business coordination.
- `models/`: future Django ORM definitions owned by this domain.

These directories contain no implementations. No Django app has been initialized.
Cross-domain operations use the owning service; do not duplicate entities or mutate
another domain's models directly. Open requirements are tracked in the
[question register](../../../docs/architecture/open_questions.md).
