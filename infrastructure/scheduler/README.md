<!-- Placement: infrastructure/scheduler/README.md -->
# Scheduled offer imports

A daily Tanitjobs import into **your own machine's database** (see
[infrastructure/postgres](../postgres/README.md)). It runs the same command as the admin
"Lancer l’import" button, in scheduler mode:

```
uv run python -m pipelines.ingestion.offer_import tanitjobs --scheduled --headless
```

- Keywords and pages come from the source's configuration (admin Imports page, "Modifier",
  `{"keywords": [...], "max_pages": N}`). Empty: an empty search over 2 pages (every field).
- One run per source at a time, shared with the admin button: if an import is already running,
  the scheduled run is skipped (exit code 0). An unauthorized source is refused (exit code 1).
- Each run is one import batch, visible on the admin Imports page; the audit log records it
  as a `SYSTEM` action (`imports.batch.schedule`).

## Windows (Task Scheduler)

Prerequisites: Docker Desktop running with the `mahara-postgres` container, `uv` on the PATH,
Google Chrome installed (the scraper drives it headless). No administrator rights needed.

```powershell
# daily at 07:00 (choose another time with -At 13:30)
powershell -ExecutionPolicy Bypass -File infrastructure\scheduler\register_scheduled_import.ps1
# run it once now, to test
Start-ScheduledTask -TaskName "MaharaMatch Tanitjobs import"
# remove it
powershell -ExecutionPolicy Bypass -File infrastructure\scheduler\register_scheduled_import.ps1 -Remove
```

The task runs only while you are logged in; a run missed because the PC was off starts after
the next login. Logs: `logs\imports\scheduled-<date>.log` (git-ignored).

## Linux / macOS (cron)

```
# crontab -e : every day at 07:00
0 7 * * * cd /path/to/mahara_match && uv run --frozen python -m pipelines.ingestion.offer_import tanitjobs --scheduled --headless >> logs/imports/scheduled.log 2>&1
```

## Sharing it with the team

What is shared through GitHub is the **definition** of the job: the command, these scripts and
this README. Each teammate who wants fresh offers in their local database registers the task
once with the command above. A schedule itself cannot live in the repository: it belongs to
the machine (or server) that runs it.

Since 2026-11-14 every developer has a separate local database, so one person's scheduled import
does not reach the others. A single shared schedule needs a shared database first (a restored
Supabase project or another hosted PostgreSQL). Then one always-on runner would do the imports
for everyone: a small server with this cron line, or the Dagster schedule planned in
`pipelines/dagster/`. A GitHub Actions cron is possible too, but it needs the shared database's
URL as a repository secret and a runner with Chrome, and Tanitjobs may block cloud IPs.
