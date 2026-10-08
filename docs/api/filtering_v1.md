# Phase 3B API filtering and Phase 3C training lifecycle

All routes require active authentication and retain their existing RBAC and
organization/candidate scope. Filters narrow an authorized queryset; they never
grant access. Training's existing organization and program selectors retain their
permission checks before additional filters are applied. Invalid recognized UUID,
enum, datetime or ordering values return the shared 400 error envelope. Unknown
query parameters are ignored and cannot alter authorization.

Lists retain `page` and `page_size` (20 by default, capped at 100), and the
`count`, `next`, `previous`, `results` response. Training lists now use UUIDs to
break timestamp ties. No response fields or routes were added.

| GET endpoint under `/api/v1/` | Query parameters |
| --- | --- |
| `job-offers/` | `status`, `governorate`, `city`, `work_mode`, `organization_id`, `search`, `ordering` |
| `applications/` | `offer_id`, `candidate_id`, `organization_id`, `status` |
| `offer-matches/` | `offer_id`, `candidate_id`, `model_version`, `calculated_after`, `calculated_before` |
| `training/programs/` | Existing `organization_id`; `skill_id`, `governorate`, `delivery_mode`, `status` |
| `training/sessions/` | Existing required `program_id`; `organization_id`, `skill_id`, `delivery_mode`, `location`, `status`, `starts_after`, `starts_before`, `ends_after`, `ends_before` |
| `training/enrollments/` | Existing `organization_id`, `candidate_id`; `session_id`, `status` |
| `audit-logs/` | `actor_id`, `action`, `entity_type`, `entity_id`, `created_after`, `created_before` |
| `import-batches/` | `source_id`, `status`, `started_after`, `started_before`, `completed_after`, `completed_before` |
| `import-batches/{batch_id}/rows/` | Existing batch path scope; `source_id`, `status`, `created_after`, `created_before` |

UUID parameters refer to the existing resource/catalog UUIDs. Governorate and
city match exactly, ignoring case. Job `search` matches only title or description
using case-insensitive substrings; it does not inspect creator identity, candidate
data, application text, match explanations, CVs, audit payloads or import JSON.
Job ordering accepts `created_at`, `published_at`, `title`, or their `-` descending
forms, with UUID as a tie-breaker. The default ordering is unchanged.

Other string filters match exactly. Training skill filters include both taught
and prerequisite skills and return each result once. Program governorate refers
to the provider's governorate; session `location` matches a substring of the
existing `location_or_url` field. Delivery mode is `ONLINE`, `PRESENTIAL` or
`HYBRID`; work mode is `REMOTE`, `HYBRID` or `ONSITE`. Status filters use each
resource's existing states. Import batches accept `STARTED`, `COMPLETED`, `FAILED`;
rows accept `ADDED`, `UPDATED`, `UNCHANGED`, `REJECTED`.

Date filters accept ISO 8601 datetimes, with inclusive boundaries. A supplied end
must not precede its corresponding start. Matches have no modeled freshness or
status field, so only model version and calculation dates are filterable.

## Approved training lifecycle

- New enrollment is rejected when the current time is strictly after
  `registration_deadline`, using `training_registration_closed`. The exact
  deadline instant remains eligible. The service permits absence of a deadline,
  but the current model/API still requires one; no nullable field was introduced.
- `REGISTERED`, `IN_PROGRESS`, `COMPLETED` consume capacity. `DROPPED` does not.
  A full session returns `training_session_full`. Capacity updates cannot reduce
  the limit below occupied capacity.
- The existing candidate/session uniqueness rule remains. A dropped candidate
  cannot re-enroll; duplicate attempts return `training_duplicate_enrollment`.
- Progress follows `REGISTERED → IN_PROGRESS → COMPLETED`. A registered
  enrollment cannot jump directly to 100%. Progress must be finite and within
  0–100. Completed/dropped enrollments cannot receive progress changes.
- Dropping a completed enrollment is forbidden. Repeated drop is idempotent.
  The existing candidate/provider permissions govern drop operations, including
  for cancelled sessions.
- Session cancellation preserves every enrollment row and status. Cancelled
  sessions reject new enrollment and progress changes. Completed/cancelled
  sessions cannot change status through update or delete; no reopen action exists.
- Enrollment, progress, drop, capacity changes and cancellation run in
  transactions and lock the session row first. Progress/drop then lock and reload
  the enrollment row. This serializes capacity decisions and lifecycle writes
  and prevents stale objects from reversing terminal states. Database uniqueness
  remains the final duplicate-enrollment guard.

Provider actions retain organization-scoped permissions. No scoring, notification,
refund, attendance, certificate or frontend behavior was added. The concurrency
tests require an isolated database supporting `SELECT FOR UPDATE`; SQLite skips
those tests because it cannot validate PostgreSQL row locks.
