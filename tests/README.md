# Future verification boundaries

- `unit/backend/`, `unit/ai/`, `unit/pipelines/`: isolated behavior in each subsystem.
- `integration/`: service collaboration, ORM/storage adapters and projection paths.
- `e2e/`: complete user journeys through public application boundaries.

Identity contract unit tests now exist. PostgreSQL-backed identity tests remain gated
on the shared P4 organization models and initial identity migration.

Add meaningful scenarios alongside implementation: domain ownership and access
checks, candidate confirmation, external-action confirmation, cited answers and
missing-data handling, application history, and idempotent projection updates.
Resolve corresponding open questions before encoding business expectations.
Fixtures must use synthetic data; never commit real CVs or credentials.

Coverage is configured for `backend`, `ai` and `pipelines`. Request it explicitly
with `uv run --frozen pytest --cov --cov-report=term-missing` once tests exist.

## PostgreSQL integration tests

Set `TEST_DATABASE_URL` (preferred) or `DATABASE_URL` to a PostgreSQL connection
URL to run integration tests against an external database such as Supabase:

```powershell
$env:TEST_DATABASE_URL = "postgresql://user:password@host:5432/database?sslmode=require"
uv run pytest tests/integration -m "not ollama"
```

The database must have the `vector` extension installed, and the supplied role
must be allowed to create and drop schemas and run Django migrations. Tests run
inside a randomly named schema that is dropped after the session; use a direct
connection or Supabase session pooler, not a transaction pooler. `TEST_DATABASE_URL`
takes precedence when both variables are set. This mode does not use Docker or
Testcontainers.
