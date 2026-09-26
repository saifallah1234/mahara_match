# Training

Owns provider programs, taught and prerequisite skills, sessions, candidate
enrollments and explainable recommendations. Organization, candidate and skill
references point to their owning domains; historical links are protected.

Training managers receive organization-scoped permissions for `TRAINING_PROVIDER`
organizations. Candidates enroll against their candidate profile. Training prices
are TND: free programs cost `0`, paid programs cost more than `0`.

Seed identity and training permissions with `python manage.py seed_rbac` after
the required database migrations have been applied. The initial training migration
is applied. Capacity and registration-deadline policies beyond the existing
session fields, and recommendation scoring criteria, remain open in the
[question register](../../../docs/architecture/open_questions.md).
