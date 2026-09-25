# Candidate API v1 contract

The candidate, document and taxonomy apps are implemented without migrations. Full
model checks await `recruitment.JobOffer` for targeted analyses and the identity
app's pending `Organization` model. Database tests await shared migrations.

- `/api/v1/candidate-profiles/me/`: GET, POST (create once), PUT and PATCH for the
  current candidate. `completion_score` and identity linkage are system managed.
- `/api/v1/experiences/`, `/educations/`, `/candidate-languages/`,
  `/candidate-skills/`, `/certifications/`, `/candidate-preferences/`, `/projects/`
  and `/cvs/`: candidate owned list, create, retrieve, PUT and PATCH. No DELETE.
- `/api/v1/documents/`: owner scoped list and retrieve. Storage metadata creation
  is available to trusted application services, not the HTTP API. The storage URI
  is never returned by the candidate document endpoint.
- `/api/v1/skills/`, `/languages/`, `/education-levels/`: authenticated read only
  reference catalogs.
- `/api/v1/cv-analysis-results/`: candidate owned read only ATS results.

Candidates need an active global `CANDIDATE` role for candidate records. Another
candidate's record returns 404. Recruiter reads are not exposed yet, regardless of
stored profile visibility. CV creation requires an existing owned document. Its
version number is allocated per candidate and at most one CV can be primary.
Scan/parse results, raw parsed JSON, skill validation provenance, completion scores
and ATS analysis results have no candidate write route. Only candidate confirmed
information is written to structured records.

**Approved change pending implementation (2026-09-25; Q09):** one
`candidate_preferences` record per candidate must contain work mode, relocation
and maximum preferred commute distance in kilometres. Missing distance means no
preference stated. The current code/API still puts `distance` and `relocation` on
`candidate_profiles`; this contract describes that current behavior until P2
reconciles it before migration. Its decimal field currently represents up to
999.99 km. `relocation` is `OPEN` or `CANNOT`; `work_mode` is `REMOTE`, `HYBRID` or
`ONSITE`. Language levels use CEFR A1–C2; skill levels use `BEGINNER`,
`INTERMEDIATE`, `ADVANCED` and `EXPERT`. Project `technologies` accepts skill UUIDs.
