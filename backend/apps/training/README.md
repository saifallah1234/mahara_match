# Training

Owns provider programs, taught and prerequisite skills, sessions, candidate
enrollments and explainable recommendations. Organization, candidate and skill
references point to their owning domains; historical links are protected.

Training managers receive organization-scoped permissions for `TRAINING_PROVIDER`
organizations. Candidates enroll against their candidate profile. Training prices
are TND: free programs cost `0`, paid programs cost more than `0`.

Seed identity and training permissions with `python manage.py seed_rbac` after
the required database migrations have been applied. The initial training migration
is applied. Approved Phase 3C deadline, capacity, cancellation and terminal-state
rules are implemented; see the [API/lifecycle contract](../../../docs/api/filtering_v1.md).
Recommendation scoring, assessment, attendance and certificates remain outside
this phase.
