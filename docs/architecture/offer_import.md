# Job-offer import: decisions and open items

Moved from `CLAUDE.md` (2026-10-21). The pipeline structure, rules, gotchas and commands
stay in [CLAUDE.md](../../CLAUDE.md). Do not re-litigate the decisions below without asking.

## Decisions already made

- Scraped offers are saved as `PUBLISHED` (with `published_at` = import time) and `easy_apply = False`
  (candidates apply on the original site). Changed from `DRAFT` on 2026-11-14 by the import owner, see the
  [decisions log](decisions_log.md). A later import never changes the status, so closing or unpublishing
  an offer by hand sticks. `publish_imported_offers` (`--dry-run` first) publishes the drafts left by
  earlier runs.
- The placeholder organization is `VERIFIED` (candidates only see offers of verified organizations).
  A `PENDING` placeholder is promoted on the next run; `REJECTED` is kept and hides every imported offer.
- Automatic runs (admin button, later the scheduler) use the source's `configuration_json`
  (`{"keywords": [...], "max_pages": N}`), else an empty search over 2 pages: every field, not only IT
  (decision 2026-11-14). Tanitjobs does not list strictly newest first, so a short run can miss some new
  offers; known offers are skipped, so later runs catch up. One run is one batch, whatever the keywords.
  Changing only `keywords` / `max_pages` keeps the source's authorization; any other configuration key,
  the type or the base URL still revokes it (decision 2026-11-14).
- A daily scheduled run (`offer_import tanitjobs --scheduled`) uses the same plan and the same one-run-at-a-time
  guard as the button; it is skipped while another run is going. Setup: [infrastructure/scheduler](../../infrastructure/scheduler/README.md).
- An admin starts a run from Imports ("Lancer l’import", `POST /api/v1/data-sources/{id}/run-import/`) for an
  authorized `WEB_SCRAPING` source. The scrape runs as a separate process (`offer_import --batch-id`).
- Expired offers (deadline before today) are hidden from candidates at read time for every offer,
  imported or not; nothing closes them. A fresh import is what brings current offers.
- The real employer is shown from `company_name`: the offer API returns it and the offer pages display it
  instead of the placeholder's name.
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
