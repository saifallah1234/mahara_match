<!-- Placement: CLAUDE.md (repository root, the folder that contains backend/, pipelines/ and pyproject.toml) -->
@AGENT.md
@CONTEXT.md

# Mahara Match: job-offer import (notes for Claude)

This file records rules for the scraping/import pipeline. `AGENT.md` and
`CONTEXT.md` (imported above) remain the authority on architecture; if they conflict
with this file, say so instead of picking one.

## Working conventions

- Run every command from the repository root (the folder with `pyproject.toml`), using `uv run`.
- The developer works on Windows (PowerShell). Use PowerShell-friendly commands.
- Django settings: `--settings=backend.config.settings.development`.
- The database is Supabase PostgreSQL, reached through `POSTGRES_SESSION_POOLER` in `.env`.
  It is a shared, real database: every `migrate` and every import writes to it for real.
  Never print, log or paste `.env` values.
- Every new file starts with a comment naming its placement (`# Placement: path/to/file.py`).
- New dependencies need a one-line justification (see `AGENT.md`); add them with `uv add`.
- Lint/type checks: `uv run ruff check .` and `uv run mypy .` (confirm against the repo's real config).

## Import pipeline: structure

```
tanitjobs.py (browser) -> ScrapedOffer -> offer_adapter.py -> services -> job_offers (DRAFT)
```

| File | Role |
| --- | --- |
| `pipelines/ingestion/scraped_offer.py` | Plain dataclass, raw values only, `None` = not shown. Not a model. |
| `pipelines/ingestion/tanitjobs.py` | Reads cards + detail page + info box. No interpretation. |
| `pipelines/ingestion/offer_vocabulary.py` | Lookup tables only (work modes, contract kinds, experience labels, governorates, countries). |
| `pipelines/ingestion/language_detection.py` | `lingua` restricted to fr/en/ar; returns a code or `None`. |
| `pipelines/ingestion/offer_adapter.py` | The only place that knows `job_offers` columns. Pure Python. |
| `pipelines/ingestion/offer_import.py` | Entry point (`python -m ...`). Never imports Django models. |
| `backend/apps/imports/services/batch_processing.py` | Source authorization, batch and row bookkeeping. |
| `backend/apps/recruitment/services/import_reconciliation.py` | Add / update / unchanged per (source, external_id). |
| `backend/apps/taxonomy/management/commands/seed_languages.py` | Idempotent seed of fr/en/ar. |

Rules:

- `pipelines/` never imports Django models. Only services touch the ORM.
- The adapter is pure (no Django, no browser). Priority rules between sources live there.
- If `job_offers` columns change, update the adapter's `to_model_fields()` and add a drift test
  (adapter fields must be a subset of the model's fields).
- Scrapers report only what the page showed. Defaults are applied by the adapter.

## Decisions and open items

Import decisions and open items are in [docs/architecture/offer_import.md](docs/architecture/offer_import.md).
Do not re-litigate them without asking.

## Gotchas

- Sync Playwright keeps an asyncio loop running while the browser is open, and Django refuses ORM calls
  then. `run_import` therefore has two phases: collect offers in the browser, then write to the database.
- `BaseScraper.start_browser` already opens the base URL (and solves captchas automatically).
  Do not `goto` the same URL again right after it.
- Calling `.first` / `inner_text()` on a Playwright locator that does not exist waits for the timeout.
  Check `count()` first for optional elements.
- `--refresh` revisits stored offers and updates them. It never changes `status`, organization or
  creator, and it skips soft-deleted offers.

## Commands

```
uv run python backend/manage.py seed_languages --settings=backend.config.settings.development
uv run python -m pipelines.ingestion.offer_import tanitjobs "python" --max-pages 1
uv run python -m pipelines.ingestion.offer_import tanitjobs "python" --max-pages 1 --refresh
uv run python backend/manage.py makemigrations --check --dry-run --settings=backend.config.settings.development
```

## Agent skills

- Issues and specs: local markdown under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.
- Triage labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`): `docs/agents/triage-labels.md`.
- Domain docs: `GLOSSARY.md` and `docs/adr/`. See `docs/agents/domain.md`.
