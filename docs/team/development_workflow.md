# Team development workflow

## Environment and branches

Use Python 3.12 and `uv sync --locked`. Work on short-lived branches such as
`feature/<domain>-<purpose>`, `fix/<domain>-<purpose>` or `docs/<purpose>`.
Keep each branch focused on one reviewable change. No branches or remote policies
are created by this scaffold.

In a Git checkout, install local checks with `uv run --frozen pre-commit install`.
Before a PR, run Ruff lint/format checks, mypy and relevant tests using the commands
in the root README. No test suite exists yet; report pytest's empty-suite result
honestly. Once tests exist, failures must be resolved before merging.

## Pull requests and review

Use the PR template. Explain the problem, affected domain boundaries, behavior,
verification, migration implications and documentation changes. At least one
non-author reviewer must approve; request the affected module owner or backup.
Avoid unrelated refactors and cross-module edits hidden inside feature work.
The team must configure branch protection later; these rules are not automated yet.

## Phase-aware ownership for five people

Use the [implementation roadmap](implementation_roadmap.md) for phase assignments
and the [Phase 1 execution plan](phase_01_data_backend.md) for exact entity/file
ownership. This agreed allocation replaces the original scaffold's example template.
Assign real names to Person 1–5 together; do not infer them from PDF author order.

| Slot | Phase 1 accountability | Later workstream / coordination | Backup reviewer |
| --- | --- | --- | --- |
| Person 1 | Identity users/RBAC, assistant/platform records, Django integration | Access, confirmation/audit, root backend configuration and dependencies | Person 4 |
| Person 2 | Candidates, documents, shared taxonomy | CV processing integration, candidate journeys, evidence/evaluation | Person 5 |
| Person 3 | Recruitment and persisted offer matches | Offer/application workflows, search, matching and retrieval | Person 2 |
| Person 4 | Identity organizations/members, import records, PostgreSQL/CI | Imports, infrastructure, UI integration, ANETI AI advisor/LangGraph runtime | Person 1 |
| Person 5 | Training; taxonomy consumer test support | Training recommendations/participation, OCR, Dagster, graph context and evaluation | Person 2 |

Person 1 and Person 4 share the identity app through separate model/API/service
files. Person 1 integrates its exports, routes and migration sequence after joint
review. Person 2 owns shared reference concepts even when other people consume
them. Person 4 owns organizations of every type, including training providers;
Person 5 owns training programs and participation, not duplicate organizations.
Later task cards explicitly delegate particular files across these review areas;
they do not transfer domain ownership. Guidance is a scope marker for AI support,
not a human advisor staffing module.

Tests and feature documentation follow the module owner. Root context, agent
instructions, shared architecture, dependency policy and CI decisions are shared
team concerns. Backup reviewers support continuity; ownership is not exclusive
write access and does not authorize unrelated changes.

Use task IDs in branches/PR descriptions, for example
`feature/p01-2-candidate-records`. Merge agreed contracts before their consumers,
then integration tests. The roadmap identifies likely shared-file conflicts and
PR order per phase. Frontend file ownership is assigned only after its framework,
location and testing contract are agreed at F01; no UI_ROOT placeholder is a real path.

## Cross-module and architecture changes

Prefer the owning service's public contract over edits to another module's internals.
Discuss contract changes with the affected primary/backup owner before coding.
Do not create duplicate domain entities to avoid coordination. Keep pure technical
helpers in common; do not relocate business state there.

For shared architecture changes, describe the problem, alternatives, chosen
boundary and affected modules in the PR; obtain review from affected owners and
at least one other team member. Record the agreed decision in architecture docs,
update CONTEXT.md and the ownership map, and resolve related question-register
entries. Consult the source documents; ambiguity is documented, not guessed.

## Migration coordination when Django begins

The domain owner authors and reviews migrations with the feature. Agree changes
to shared identities, relationships and auth configuration before generating them.
Rebase on the latest shared branch before generating migration files; coordinate
parallel changes to the same app and resolve migration graph conflicts explicitly.
Never renumber/delete another developer's migration or rewrite an already shared
or applied migration without team coordination. Commit migrations with models.
Verify future changes on a clean database and an upgrade path. Django ORM remains
the schema authority; no parallel manual DDL or infrastructure-created tables.

## Dependencies and lockfile

Explain why each dependency is needed and which domain/capability uses it. Prefer
existing tools and the standard library. Runtime additions belong with actual
implementation; use `uv add --dev <package>` for development-only tools.
Update and review pyproject.toml and uv.lock together. A deliberate version refresh
uses `uv lock --upgrade-package <package>`; normal setup uses `uv sync --locked`.
Do not hand-edit uv.lock during conflicts: reconcile declarations, regenerate with
uv, and review the resolved diff. Ruff handles formatting; do not add Black.

Keep real secrets, uploaded CVs, database volumes and downloaded models out of Git.
Use synthetic fixtures and the blank placeholders in .env.example.
