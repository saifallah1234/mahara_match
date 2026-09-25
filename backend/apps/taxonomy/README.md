# taxonomy

**Responsibility:** Shared canonical references reused across business domains.

**Logical entity ownership:** skills, skill_aliases, languages, education_levels.

**Sources:** DM §§3.1, 4.B; PDF pp. 4, 9. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Candidate, offer and training associations stay with those domains. Occupation taxonomy and reference scales are unresolved.

## Reserved boundaries

- `api/`: authenticated read-only catalog transport.
- `models/`: Django ORM reference definitions.

The app is initialized without migrations. Reference governance beyond Django admin
and a skill alias contract remain future work.
Cross-domain operations use the owning service; do not duplicate entities or mutate
another domain's models directly. Open requirements are tracked in the
[question register](../../../docs/architecture/open_questions.md).
