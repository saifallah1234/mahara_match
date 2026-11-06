# Job-offer import: decisions and open items

Moved from `CLAUDE.md` (2026-10-21). The pipeline structure, rules, gotchas and commands
stay in [CLAUDE.md](../../CLAUDE.md). Do not re-litigate the decisions below without asking.

## Decisions already made

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
