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
- `/api/v1/cv-review-roles/`: candidate read only list of role profiles (`id`, `label`,
  `version`) an ATS analysis can target. v1: `data_engineer`, `software_engineer`.
- `/api/v1/cv-analysis-results/`: candidate owned ATS analyses. `POST` with `cv`,
  `role_profile_id` and `level` (`intern`, `junior`, `mid`) runs the analysis
  synchronously and returns 201 with the stored result. The CV must be owned, not
  deleted and still have its bytes (deleted or another candidate's CV: 404; purged
  bytes: 400). Unknown role or level, a file other than PDF/DOCX, or a non-English CV
  return 400 and store nothing. List and retrieve return `role_profile_id`,
  `role_profile_version`, `level`, `breakdown_json` (six component scores, weights,
  `ats_readiness`, `role_fit`, `parse_degraded`, counts), `issues_json` (code,
  severity, component, French message, params) and `cv_draft_json` (the CV draft, see
  below). `breakdown_json.structure` snapshots the parsed entries and skills lines; bullet
  keys such as `experience.0.2` index into it. `target_offer` stays unused. The analysis never changes the profile.
  The local chat model structures the experience, projects and education sections (one
  call per section, JSON schema, every value checked against the section text) and the
  structure is cached on the CV (`parsed_data_json` with `checksum` and
  `parser_version`, `parse_status` `parsed` or `degraded`). A rerun on the same file and
  parser version skips the model; a degraded parse is retried. If the model is down or
  its output fails validation, the analysis uses the line-based split and
  `parse_degraded` is true.
- `/api/v1/cv-analysis-results/{id}/rewrite/`: `POST {"bullet": "experience.0.2"}`
  rewrites one experience or project bullet with the local model (temperature 0.4, role
  verbs, metric hints and the 3 closest role examples by `bge-m3`, else the first 3). The
  rewrite is rejected if it adds a number, role skill or capitalised name absent from the
  original (`[X]` placeholders allowed), exceeds 25 words or one line; one retry at 0.1,
  then `source: "rule"` with a French `suggestion` and `text: null`. Nothing is stored.
- `/api/v1/cv-analysis-results/{id}/summary/`: `POST` proposes a professional summary
  from the structure and role label, same validator against the CV's facts (two
  sentences, at most 60 words, one line). Nothing is stored.
- `/api/v1/cv-analysis-results/{id}/draft/`: `PATCH` with exactly one change:
  `bullet` + `decision` (`accept` with `text`, also used for an edit, or `reject`);
  `skill` + `has_experience` for a missing core skill of the analysis (only a yes adds it
  to `confirmed_skills`; others go to `declined_skills`); or `summary` (empty clears).
  `cv_draft_json` is `{bullets: {key: {original, decision, text}}, confirmed_skills,
  declined_skills, summary}`. The model never adds a skill; the profile is never changed.
  Another candidate's analysis returns 404 on all three routes.
- `/api/v1/cv-analysis-results/{id}/generate/?file_format=pdf|docx` (default `pdf`):
  `GET` downloads the CV draft as an ATS-friendly file (one column, standard English
  headings in the role's section order, `•` bullets, no tables, icons or images, a real
  PDF text layer). Content is the original CV's sections with accepted rewrites, the
  accepted summary and confirmed skills applied. Nothing is stored. Warnings, not
  refusals: `X-CV-Placeholders` counts unresolved `[X]` placeholders and
  `X-CV-Missing-Sections` lists sections the level requires that the CV lacks.
- `/api/v1/cv-analysis-results/{id}/save-cv/`: `POST {"file_format": "pdf"|"docx"}`
  stores the generated file as a new `CV` document and returns the new CV (201): next
  per-candidate version number, not primary, `language_code` `en`. The UI asks for
  explicit confirmation first. The profile is never changed. 404 for another
  candidate's analysis, as above.

Candidates need an active global `CANDIDATE` role for candidate records. Another
candidate's owned record returns 404. Recruiter discovery does not grant access to
candidate-owned record endpoints. CV creation requires an existing owned document. Its
version number is allocated per candidate and at most one CV can be primary.
Scan/parse results, raw parsed JSON, skill validation provenance and completion
scores have no candidate write route; ATS analyses are created only by the analysis
endpoint above. Only candidate confirmed
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
must be `RECRUITERS` or `PUBLIC`; `PRIVATE` is excluded. PUBLIC is a superset of
RECRUITERS for verified recruiters (Q28, decided 2026-10-15); it never grants
anonymous access. Detail uses the same authorized visibility queryset as list;
private and inactive candidates return 404.

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
