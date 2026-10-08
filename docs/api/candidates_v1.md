# Candidate API v1 contract

The candidate, document, taxonomy, recruitment and identity apps have applied
initial migrations. Integration tests cover access, upload, download and deletion.

- `/api/v1/candidate-profiles/me/`: GET, POST (create once), PUT and PATCH for the
  current candidate. `completion_score` and identity linkage are system managed.
- `/api/v1/candidate-profiles/` and `/api/v1/candidate-profiles/{id}/`: recruiter
  discovery list and detail (GET only), with the redacted contract below.
- `/api/v1/experiences/`, `/educations/`, `/candidate-languages/`,
  `/candidate-skills/`, `/certifications/`, `/candidate-preferences/`, `/projects/`
  and `/cvs/`: candidate owned list, create, retrieve, PUT and PATCH. CV versions
  also support DELETE; structured profile records do not.
- `/api/v1/documents/`: owner scoped list and retrieve, multipart upload with
  `file` and `type=CV`, and authenticated `/documents/{id}/download/`. The storage
  URI is never returned by the candidate document endpoint.
- `/api/v1/skills/`, `/languages/`, `/education-levels/`: authenticated read only
  reference catalogs.
- `/api/v1/cv-analysis-results/`: candidate owned read only ATS results.

Candidates need an active global `CANDIDATE` role for candidate records. Another
candidate's owned record returns 404. Recruiter discovery does not grant access to
candidate-owned record endpoints. CV creation requires an existing owned document. Its
version number is allocated per candidate and at most one CV can be primary.
Scan/parse results, raw parsed JSON, skill validation provenance, completion scores
and ATS analysis results have no candidate write route. Only candidate confirmed
information is written to structured records.

Deleting a CV hides it from the candidate CV/document lists and prevents new
applications with it. An existing application retains its exact file while open.
After deletion, a closed application cannot download the file, even if another
open application still can. Object bytes are purged when the CV has no applications
or every linked application is rejected. Metadata and application references stay.
The idempotent `purge_deleted_cvs` management command retries storage failures;
schedule it daily in deployment.

One `candidate_preferences` record per candidate contains work mode, relocation
and maximum preferred commute distance in kilometres (Q09). Missing distance means no
preference stated. Its decimal field currently represents up to
999.99 km. `relocation` is `OPEN` or `CANNOT`; `work_mode` is `REMOTE`, `HYBRID` or
`ONSITE`. Language levels use CEFR A1–C2; skill levels use `BEGINNER`,
`INTERMEDIATE`, `ADVANCED` and `EXPERT`. Project `technologies` accepts skill UUIDs.

## Phase 3A recruiter discovery

Discovery requires an active authenticated account with an organization-scoped
`RECRUITER` role granting `candidates.profile.discover`, membership in that same
organization, and a verified, non-deleted `COMPANY` or `SUBSIDIARY` organization.
`seed_rbac` seeds this permission for recruiters only. ADMIN, ministry roles and
superuser status do not bypass these requirements; the permission is revocable.

The candidate account must be ACTIVE and not soft-deleted, and its visibility
must be exactly `RECRUITERS`. This is the explicit recruiter-discovery opt-in
state for Phase 3A. `PRIVATE` and `PUBLIC` are excluded. PUBLIC semantics remain
undefined and never grant anonymous access. Detail uses the same authorized
visibility queryset as list; hidden and inactive candidates return 404.

List and detail return the same redacted fields:

- `id`: candidate profile UUID for detail lookup.
- `headline`, `governorate`.
- `skills`: skill catalog UUID, level and years of experience.
- `experiences`: organization name, job title, start and end dates.
- `educations`: education-level catalog UUID, institution, field of study, start
  and end years.
- `preferences`: work mode, relocation and maximum commute distance; null when
  no preference record exists.

No user identity, contact details, birth date, city, summary, desired job title,
availability, completion score, visibility setting, timestamps, validation
provenance, free-text history descriptions, CVs, documents or storage data are
returned. CV access remains exclusively governed by the existing application
workflow. The professional related models have no soft-delete state; soft-deleted
accounts and their related content are excluded, and CVs are never included.

Optional list filters are `skill` and `education_level` (catalog UUIDs),
`governorate` (case-insensitive exact match), `work_mode` (`REMOTE`, `HYBRID`,
`ONSITE`), `relocation` (`OPEN`, `CANNOT`) and `search` (case-insensitive substring
of headline, skill canonical name or experience job title). Filters combine with
AND and apply only after authorization and visibility restrictions. Invalid UUIDs
or enum filters return the shared 400 error envelope. Unknown parameters cannot
alter the visibility queryset.

Pagination uses the standard `page` and `page_size` contract: default 20, maximum
100, with `count`, `next`, `previous` and `results`. UUID ordering is deterministic;
there is no ranking, scoring or semantic search. Candidate self access is unchanged.
