# Mahara Match context

## Sources and status

The [logical MVP data model](mahara_match_data_modeling.md) (DM) and the
[preliminary specification](Cahier%20de%20charge%20pr%C3%A9liminaire%20PDF.pdf) (PDF)
are the business sources of truth. PDF citations throughout this repository use
**physical PDF page numbers**, including the cover (printed page 8 is physical
page 9). Identity, candidates, training, recruitment and persisted match models
have partial implementations; several planned workflows remain.

Dated decisions (2026-09-20 onward) are in the [decisions log](docs/architecture/decisions_log.md).
Open questions are in the [question register](docs/architecture/open_questions.md).
Key points that still shape the design:

- The ANETI employment advisor is the system's AI agent, not a human advisor account
  (Q22). It supersedes the human-role reading of DM §2.
- Five human roles: Candidate, Recruiter, Training Manager, Ministry Manager, Admin.
- Offers use TND only. Training prices are TND, free `0` or paid greater than `0`.
- Frontend is React, TypeScript and Vite under `frontend/`, French-only for the MVP.
- Candidate registration activates immediately; recruiter/provider access waits for admin verification.
- Applying or enrolling discloses the candidate's name, e-mail and limited profile to that organization only (Q32, [ADR 0001](docs/adr/0001-applicant-identity-disclosure.md)).
- Retained-data policy still needs review before release.

The task adds technical decisions not stated in those documents: a Django/DRF
modular monolith, Django ORM as schema authority, Python 3.12, uv, and the chosen
development tooling. These are scaffold decisions, not claims about the sources.

## Objective and actors

Support access to employment in Tunisia through structured professional profiles,
CV preparation, explainable job/training recommendations, recruitment follow-up
and communication. Automate repetitive tasks while leaving final decisions to
candidates and employers (PDF p. 2; advisor identity clarified above).

| Actor | Responsibility |
| --- | --- |
| Candidate | Maintain profile/CVs, search, apply and follow employment/training progress |
| Employer / recruiter | Represent organizations, publish offers and manage recruitment |
| ANETI employment advisor (AI agent) | Recommend jobs/training, assist candidates and propose CV corrections/improvements |
| Training manager | Manage provider catalogues, sessions, enrollment and skills acquisition |
| Ministry manager | Analyze aggregated employment and training indicators |
| Administrator | Manage access, organizations, reference data, moderation and audit |

The five human actors use account roles, with organization membership where
applicable (DM §2; PDF pp. 3–4). The ANETI advisor is a system AI actor, not a
sixth human role or an advisor staffing workflow. Ministry reporting still needs
approved KPI and privacy contracts; AI guidance reuses candidate, recommendation
and assistant data.

## Functional modules and vocabulary

PDF pp. 4–6 describes accounts/organizations; candidate profiles and CV
intelligence; search/matching/GraphRAG; the Tunisian conversational assistant;
employers/offers/applications; training/community; and data engineering,
infrastructure and MLOps.

- **Organization:** company, subsidiary, training provider, ANETI structure or ministry.
- **User:** the authentication account shared by every human actor; it is distinct
  from the actor's candidate profile or organization membership.
- **Role:** a named bundle of platform authority such as candidate, recruiter or
  administrator; it is not an organization membership.
- **Permission:** one allowed operation on a protected resource.
- **Role assignment:** the link granting a role to a user globally or within one
  organization. Organization-scoped assignments do not replace membership.
- **Candidate profile:** the user's structured professional record. A **CV** is a
  versioned document representation; a **document** is shared stored-file metadata.
- **Skill:** one canonical reference reused by candidates, offers and training.
- **Application:** a candidate's submission to an offer using a particular CV version.
- **Offer match:** a versioned recommendation score and explanation, not an application.
- **Training program / session / enrollment:** catalogue item, scheduled occurrence,
  and candidate participation respectively. Academic education remains candidate data.
- **Agent action:** a proposed/confirmed/executed business action associated with an
  assistant execution, including actions proposed by the ANETI AI advisor.
- **Import batch / row:** source ingestion history, not an alternative offer database.

The complete entity-to-domain map is in
[domain boundaries](docs/architecture/domain_boundaries.md).

## Technical and persistence architecture

The backend is a modular monolith: DRF API → application service → Django
ORM → PostgreSQL. Django migrations create and evolve relational tables.
Initial migrations for all active business apps were generated and applied to the
configured Supabase PostgreSQL database on 2026-09-26 (development moved to a local
restored copy on 2026-11-14, see the decisions log). RBAC roles and permissions
were seeded. Assistant, imports and platform have protected persistence interfaces;
the agent runtime and actual import processing remain in later phases.

PostgreSQL owns transactional data, initial text search and the derived pgvector
embedding index in `matching.embeddings`. The index retains source entity types
and relational UUIDs. bge-m3 (1024 dimensions) is configured; final model
selection remains open. Vectors carry no scope: every read pre-filters by the IDs
the owning domain says the caller may see.
Object storage holds CVs and other original files; the database holds metadata
and URIs. Use Neo4j only if GraphRAG traversal genuinely needs it. Validated
changes are recorded in PostgreSQL before idempotent synchronization (DM §§1, 5;
PDF p. 9).

The PDF's microservice deployment wording (p. 10) is overridden by this task's
modular-monolith requirement. Future heavy processing can have separate execution
processes without creating independent business services or schema ownership.

## AI and agentic workflows

Mock interviews (assistant-owned rehearsal sessions, separate from recruitment appointments),
their configuration and release gates: see the [decisions log](docs/architecture/decisions_log.md)
(2026-10-11), the [runbook](docs/deployment/mock_interviews.md) and the
[API contract](docs/api/mock_interviews_v1.md). No deployment or real GPU inference has occurred.

The ANETI employment advisor is the AI agent of the system. Its future reasoning
and orchestration live in `ai/agents/` and `ai/workflows/`; CV capabilities live in
`ai/document_intelligence/`. It uses tools and owning application services for
recommendations and CV corrections, with interaction history in `assistant`.
It does not introduce a human advisor account, assignment entity or duplicate
candidate, CV or recommendation record.

The assistant supports French, Arabic and Tunisian dialect, uses accessible
internal information, cites sources and states when data is absent (PDF p. 7).
Qwen is discussed as an MVP candidate; final provider/model selection remains open.

LangGraph is planned for interactive multi-step paths combining tools,
deterministic steps and human validation. Agents call tools, tools call application
services, and those services enforce permissions and persistence. Conversation,
execution, tool-call and action records belong to the backend `assistant` domain.
Agent-initiated profile edits, applications, enrollments and external sends require
explicit user confirmation; reads and drafts do not. Action persistence uses
idempotency keys. Exact lifecycle states remain a P1 contract (Q15).

CV processing separates text extraction (PyMuPDF) and OCR for scanned/image inputs
(Tesseract or equivalent) from NLP/LLM parsing, ATS analysis and CV generation.
Extracted profile information must be confirmed by the candidate. Under G05, raw
CV results are stored separately from candidate-validated normalized data and
remain linked to the CV without an age-based automatic deletion timer. Account
deletion is soft deletion; deleted CV bytes follow the eligibility rule in the
decisions log (2026-09-25 refinements). Retained-data policy still needs review before release
(DM §4.B; PDF p. 9).

RAG uses retrieved internal sources; GraphRAG adds relationships among
candidates, organizations, offers, skills and training. Hybrid lexical/vector/graph
retrieval and reranking support source-backed explanations of matched and missing
skills. Neither retrieval nor model output can replace business authorization or
make final hiring decisions (PDF pp. 2, 5, 7, 9). The baseline is a pilot; the MVP
label requires demonstrated and evaluated hybrid plus graph/GraphRAG retrieval.

Scoped agent retrieval: the ANETI agent serves candidates and verified recruiters;
training manager, ministry and admin retrieval is deferred (Q30). Recruiters see
limited profiles only as IDs and matched skills in assistant history (Q28, Q29).
Details and the 2026-10-15 rules: the [decisions log](docs/architecture/decisions_log.md),
the [AI architecture](docs/ai/architecture.md#scoped-retrieval-in-the-agent-2026-10-15)
and the [matching README](backend/apps/matching/README.md#production-retrieval-2026-10-15).

## Background pipelines

Dagster is planned for recurring imports, normalization, skill mapping, quality,
embedding generation, deduplication, archival and projection synchronization.
Reusable processing stays outside Dagster definitions and calls business services
for relational writes. LangGraph handles interactive flows, Dagster background
orchestration (PDF pp. 9–10).

## Repository organization and phases

`backend/apps/` owns business data/services; `backend/common/` holds domain-neutral
helpers. `ai/` owns future intelligence capabilities; `pipelines/` processing;
`infrastructure/` deployment boundaries; `tests/` verification; `docs/` decisions
and collaboration. See the [repository map](README.md#repository-map).

Guidance remains a README-only scope marker for AI-assisted candidate support,
not a human advisor module or a second AI runtime. Reporting serves demo counts only
(2026-11-07, decisions log); approved aggregate KPIs and privacy rules are still needed. Community is
post-MVP. Advanced integrations stay outside the current release; freelance,
fine-tuning and quantization retain separate future gates (PDF p. 10).

## Decisions and unresolved questions

The [implementation roadmap](docs/team/implementation_roadmap.md) assigns future
work across five people and ten integration phases, with separately gated post-MVP
extensions. The [Phase 1 plan](docs/team/phase_01_data_backend.md) covers all defined
relational entities and controlled backend interfaces. Frontend technology and
location are selected, but no frontend has been created; P4 still needs exact
feature/test paths and browser transport/acceptance contracts. These plans define
future work beyond the partial backend implementation, not completed capabilities.

Single domain ownership, ORM-controlled relational schema, derived AI indexes,
separate interactive/background orchestration, explicit action confirmation and
candidate validation guide future implementation. Python 3.12, English docs and
uv are the agreed team defaults.

Consult [open questions](docs/architecture/open_questions.md) before implementing
the contracts still open after the 2026-09-25 answers: importer ownership, KPI
definitions, provider/model evaluation, retained-data policy, scoring weights and
release thresholds. The register distinguishes approved
direction from missing details; do not invent acceptance criteria.
