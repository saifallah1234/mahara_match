# Future verification boundaries

- `unit/backend/`, `unit/ai/`, `unit/pipelines/`: isolated behavior in each subsystem.
- `integration/`: service collaboration, ORM/storage adapters and projection paths.
- `e2e/`: complete user journeys through public application boundaries.

There are no tests yet. `uv run --frozen pytest` should report no tests collected
and exit with code 5. Do not add dummy tests or an empty-suite bypass. Django
project discovery is disabled; configure real test settings when Django begins.

Add meaningful scenarios alongside implementation: domain ownership and access
checks, candidate confirmation, external-action confirmation, cited answers and
missing-data handling, application history, and idempotent projection updates.
Resolve corresponding open questions before encoding business expectations.
Fixtures must use synthetic data; never commit real CVs or credentials.

Coverage is configured for `backend`, `ai` and `pipelines`. Request it explicitly
with `uv run --frozen pytest --cov --cov-report=term-missing` once tests exist.
