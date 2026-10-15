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

Set `TEST_DATABASE_URL` (preferred), `DATABASE_URL` or `POSTGRES_SESSION_POOLER`
to a PostgreSQL connection URL to run integration tests against an external database
such as Supabase. The project `.env` is loaded by the settings, so its
`POSTGRES_SESSION_POOLER` works without exporting anything. Without one of these the
run stops with a usage error; it never creates a separate `test_*` database:

```powershell
$env:TEST_DATABASE_URL = "postgresql://user:password@host:5432/database?sslmode=require"
uv run pytest tests/integration -m "not ollama"
```

The database must have the `vector` extension installed, and the supplied role
must be allowed to create and drop schemas and run Django migrations. Tests run
inside a randomly named schema that is dropped after the session; use a direct
connection or Supabase session pooler, not a transaction pooler. Precedence is
`TEST_DATABASE_URL`, then `DATABASE_URL`, then `POSTGRES_SESSION_POOLER`. This mode
does not use Docker or Testcontainers.
