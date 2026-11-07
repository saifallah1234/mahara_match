# reporting

**Responsibility:** Aggregated ministry employment, recruitment and training indicators.

**Logical entity ownership:** none. Reporting owns no tables and never reads other
domains' tables: recruitment (`services/indicators.py`) and training
(`services/indicators.py`) expose aggregate counts, and `services/indicators.py` here
combines them.

Sources: PDF p. 4; DM §2 identifies the actor without indicator definitions (physical PDF pages, including cover).

## Current backend

- `GET /api/v1/reporting/indicators/` →
  `{ regions: [{ governorate, offers, applications, hires, trainings }], skill_gaps: [{ skill, offer_demand, training_supply }] }`.
  Aggregate numbers only: no IDs, names or per-person rows.
- Permission `reporting.indicators.read`, seeded by `seed_rbac`, granted to MINISTRY_MANAGER
  (effective only in a verified MINISTRY organization) and ADMIN. Every other role gets 403.

The figures are demo counts, not approved KPIs; see the decisions log (2026-11-07) for the
counting rules. KPI definitions and small-count privacy rules remain open (Q20 in the
[open question register](../../../docs/architecture/open_questions.md)).
