<!-- Placement: CLAUDE.md (repository root, the folder that contains backend/, pipelines/ and pyproject.toml) -->
@AGENT.md
@CONTEXT.md

# Mahara Match: job-offer import (notes for Claude)

This file records decisions and rules for the scraping/import pipeline. `AGENT.md` and
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

## Decisions already made (do not re-litigate without asking)

- Scraped offers are saved as `DRAFT` with `easy_apply = False` (candidates apply on the original site).
- Imported offers belong to one placeholder organization and a disabled import user
  (`import-bot@mahara-match.invalid`, unusable password).
- The company name is stored in `job_offers.company_name` (added column); `organization` stays required.
- Closed offers ("Offre clôturée" card tag) are not imported: the card is not opened and the row is
  recorded as REJECTED with code `OFFER_CLOSED`.
- Salaries are monthly, in TND. Only "Entre X DT et Y DT" is parsed; anything else stays empty.
- Work mode: card tag, then info box, then `ONSITE` (default applied in the adapter only).
- Contract type: first real contract kind (CDI, SIVP, KARAMA, FREELANCE, SEASONAL) from card then
  info box; `FULL_TIME` / `PART_TIME` only as a fallback. Unknown stays empty.
- Experience is stored as the site's own label ("0 à 1 an", "Débutant", ...).
- Location: country from a dictionary; governorate is Tunisia-only; city is the part before the
  governorate, or the governorate itself when it is the only part.
- The Tanitjobs posting date is kept only in `import_rows.payload_json` (no schema change for `published_at`).
- "Langue" and "Postes vacants" from the info box are kept only in the raw payload (no columns).

## Open items

- Q24: the contract-type vocabulary is provisional; confirm with the team.
- `EducationLevel` table is empty: the team is deciding the levels (proposal: Bac+N scale with EQF
  reference; "Ingénieur" sits with Bac+5). The raw "Niveau d'étude" text is already saved in the payload.
- Required-languages column on `job_offers` does not exist yet.
- Q17: a source needs `is_authorized = True` plus `permission_evidence` before an import runs. Set by a person.
- G08/Q16: the final rule for organizations of imported offers is not settled.
- LinkedIn: not started. It needs the authorization decision first (it requires a logged-in account).
  The old scrapers live in the OneTech project, not in this repository.

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
