# candidates

**Responsibility:** Structured candidate profiles and versioned CV metadata.

**Logical entity ownership:** candidate_profiles, experiences, educations, candidate_languages, candidate_skills, Certifications, candidate_preferences, projects, cvs, cv_analysis_results.

**Sources:** DM §4.B; PDF pp. 5–6, 9. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Reference shared documents and taxonomy. Raw extraction is separate from candidate-confirmed profile data. Technical parsing, ATS and generation belong in ai/document_intelligence/.

## Reserved boundaries

- `api/`: owner-scoped DRF transport and request validation.
- `services/`: candidate ownership, version allocation and business validation.
- `models/`: Django ORM definitions owned by this domain.

The candidate preference holds work mode, relocation and maximum commute distance
for one candidate. Targeted CV analysis links to `recruitment.JobOffer`.
Cross-domain operations use the owning service; do not duplicate entities or mutate
another domain's models directly. Open requirements are tracked in the
[question register](../../../docs/architecture/open_questions.md).
