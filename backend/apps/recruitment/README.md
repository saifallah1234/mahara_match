# recruitment

**Responsibility:** Offers, applications and recruitment follow-up.

**Logical entity ownership:** job_offers, offer_skills, applications, application_status_history, interviews.

**Sources:** DM §4.C; PDF pp. 3, 5–6, 10. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Reference identity organizations, candidate CV versions and taxonomy. Do not own organization copies, import histories or matching algorithms. External application tracking is not supported by the model's Easy_apply description.

## Current backend

The ORM models and scoped `/api/v1` routes exist. Employers create draft offers;
verified companies can publish offers with at least one skill, then pause, close
or archive them. External offers require an HTTPS application link. Candidates
see published offers and can submit one internal Easy Apply application with an
owned CV. Status changes create append-only history. Recruiters can schedule an
interview for an application at `INTERVIEW` and complete or cancel it; interview
feedback is recruiter-only.

`source_id` now belongs to a protected `imports.DataSource` foreign key. The
initial recruitment migration is applied. Contract and experience vocabularies,
and agent-initiated application confirmation remain follow-up
contracts. Cross-domain operations use owning services.
