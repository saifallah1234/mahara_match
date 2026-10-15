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
run stops with a usage error; it never creates a separate `test_*` database on a
shared server. Settings that name a dedicated test database in
`DATABASES["default"]["TEST"]["NAME"]` (for example
`backend.config.settings.interview_test`, a local disposable server) keep Django's
normal test-database creation instead:

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

## Fast local run (Docker Desktop on Windows, tests in WSL)

Prefer this for routine runs: the shared Supabase database answers each query in
roughly 80 ms, so a full run there takes hours, while this takes about two minutes.
Containers are disposable (tmpfs storage) and separate from the Compose MinIO.

```bash
docker run -d --name mahara-test-pg -p 127.0.0.1:55439:5432 \
  -e POSTGRES_USER=saif -e POSTGRES_HOST_AUTH_METHOD=trust \
  --tmpfs /var/lib/postgresql/data pgvector/pgvector:pg16
docker run -d --name mahara-test-minio -p 127.0.0.1:59000:9000 \
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
  --tmpfs /data minio/minio:RELEASE.2024-10-13T13-34-11Z server /data

INTERVIEW_TEST_DB_NAME=test_interview_local \
INTERVIEW_TEST_DB_HOST=127.0.0.1 INTERVIEW_TEST_DB_PORT=55439 \
INTERVIEW_TEST_MINIO=1 MINIO_ENDPOINT=http://localhost:59000 \
MINIO_ACCESS_KEY=minioadmin MINIO_SECRET_KEY=minioadmin MINIO_USE_SSL=false \
INTERVIEW_FFMPEG="$(command -v ffmpeg)" \
uv run --frozen pytest --ds=backend.config.settings.interview_test -m 'not ollama' -q

docker rm -f mahara-test-pg mahara-test-minio   # when finished
```

`interview_test` names a dedicated `test_interview_*` database, so Django creates
and drops it on that local server. Its host/port default to a native socket
cluster (`/tmp/mahara-interview-pg`, port 55439); the two `INTERVIEW_TEST_DB_*`
variables point it at the container over TCP instead, because Docker Desktop
cannot share a Unix socket with WSL. Requirements: FFmpeg on `PATH` (or
`INTERVIEW_FFMPEG`), `npm --prefix frontend run build` before the browser test,
and `uv run --frozen playwright install chromium`. The MinIO credentials are the
public Compose development defaults, not `.env` secrets.
