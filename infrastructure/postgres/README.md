<!-- Placement: infrastructure/postgres/README.md -->
# Local PostgreSQL (development)

Since 2026-11-14 development runs on a local Docker PostgreSQL instead of the shared
Supabase project, which stopped answering ("tenant/user not found"). The local data
is a restore of the Supabase backup of 2026-10-29. See the
[decisions log](../../docs/architecture/decisions_log.md).

| Item | Value |
| --- | --- |
| Container | `mahara-postgres` (`pgvector/pgvector:pg17`, restart `unless-stopped`) |
| Port | `localhost:5434` (5432 is often taken on Windows) |
| Data volume | `mahara_pgdata` (survives container removal) |
| Application database | `mahara_match_backup` (restored data, used by `DATABASE_URL`) |
| Test database | `mahara_match` (tests create and drop throwaway schemas there) |

`.env` (never committed):

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5434/mahara_match_backup?sslmode=disable
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5434/mahara_match?sslmode=disable
```

`DATABASE_URL` takes precedence over `POSTGRES_SESSION_POOLER`, so the Supabase line can stay.
`sslmode=disable` is needed: settings default to `require`, which a local server refuses.
The `postgres/postgres` credentials only exist inside this local container.

## Restore a Supabase backup

Download the `db_cluster-*.backup.gz` file from Supabase, start Docker Desktop, then from the
repository root:

```powershell
powershell -ExecutionPolicy Bypass -File infrastructure\postgres\restore_supabase_backup.ps1 `
    -BackupPath "$HOME\Downloads\db_cluster-29-10-2026@13-39-03.backup.gz"
```

The script creates the container if needed, loads the cluster dump into a throwaway database,
copies only the application schemas (`public`, `eval_graphrag`) into `mahara_match_backup`, and
drops the throwaway database. Supabase-only objects (auth, storage, vault, realtime) are skipped;
about 19 errors about them are expected. It refuses to overwrite an existing database: pass
`-Database other_name` to restore again, then point `DATABASE_URL` at it.

After a restore, check that the schema matches the code (expect "No planned migration operations"):

```powershell
uv run python backend/manage.py migrate --plan --settings=backend.config.settings.development
```

The Supabase storage export (`*.storage.zip`) of 2026-10-29 was empty, so no stored files exist.

## Day to day

Docker Desktop must be running; the container then starts on its own. Useful commands:

```powershell
docker start mahara-postgres
docker exec -it mahara-postgres psql -U postgres -d mahara_match_backup
```
