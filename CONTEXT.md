# Mahara Match context

## Sources and status

The [logical MVP data model](mahara_match_data_modeling.md) (DM) and the
[preliminary specification](Cahier%20de%20charge%20pr%C3%A9liminaire%20PDF.pdf) (PDF)
are the business sources of truth. PDF citations throughout this repository use
**physical PDF page numbers**, including the cover (printed page 8 is physical
page 9). The P1 account/RBAC slice is the first partial implementation; the rest
of the documented product remains planned.

**User clarification (2026-09-20):** the ANETI employment advisor is the system's
AI agent for recommendations and CV assistance, not a human advisor account.
This supersedes the human-role interpretation in DM §2 and the initial scaffold;
the original source files remain unchanged. See Q22 in the question register.

**Phase 1 gate decisions (2026-09-21):** the user approved the architecture direction
for G01–G10: Django `AbstractUser`, custom RBAC and JWT; UUID keys and timestamps;
role/organization-scoped access and preferred soft deletion for important records;
central taxonomy references and aliases; separate candidate preferences and raw CV
results; explicit offer salary/currency/language fields; retained recruitment history;
import provenance; controlled training/pricing fields; and protected attributable
assistant/audit traces. The exact enum vocabularies, transition matrices, limits and
retention periods not supplied by that decision remain owning-contract details and
must not be invented. See the [Phase 1 gate register](docs/team/phase_01_data_backend.md#decision-gates-before-coding-the-affected-part)
and [question register](docs/architecture/open_questions.md).

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
sixth human role or an advisor staffing workflow. Ministry account scope and the
delivery scope of AI guidance remain open; the advisor's AI identity is resolved.

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
ORM → PostgreSQL. Django migrations will create and evolve relational tables.
The project and P1 identity models/settings are initialized, while the shared
identity migration waits for P4's organization/member models.

PostgreSQL owns transactional data. Object storage holds CVs and other original
files; the database holds metadata and URIs. Vector and Neo4j stores are derived
indexes retaining relational identifiers. Validated changes are recorded in
PostgreSQL before idempotent projection synchronization (DM §§1, 5; PDF p. 9).

The PDF's microservice deployment wording (p. 10) is overridden by this task's
modular-monolith requirement. Future heavy processing can have separate execution
processes without creating independent business services or schema ownership.

## AI and agentic workflows

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
External messages and applications require explicit confirmation (PDF p. 9).

CV processing separates text extraction (PyMuPDF) and OCR for scanned/image inputs
(Tesseract or equivalent) from NLP/LLM parsing, ATS analysis and CV generation.
Extracted profile information must be confirmed by the candidate. Under the approved
G05 direction, raw CV results are stored separately from candidate-validated normalized
data; their exact retention lifecycle remains to be defined (DM §4.B; PDF p. 9).

RAG uses retrieved internal sources; GraphRAG adds projected relationships among
candidates, organizations, offers, skills and training. Hybrid lexical/vector/graph
retrieval and reranking support source-backed explanations of matched and missing
skills. Neither retrieval nor model output can replace business authorization or
make final hiring decisions (PDF pp. 2, 5, 7, 9).

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
not a human advisor module or a second AI runtime. Any distinct business state
would need justification before implementation. Reporting and community are
also reserved scopes without schemas. Community,
advanced interview scheduling and external integrations are deferred in the PDF's
recommended MVP section. Freelance is a future extension; fine-tuning and
quantization depend on data, resources and evaluation (PDF p. 10). GraphRAG MVP
timing conflicts with its progressive-extension description and is not resolved here.

## Decisions and unresolved questions

The [implementation roadmap](docs/team/implementation_roadmap.md) assigns future
work across five people and ten integration phases, with separately gated post-MVP
extensions. The [Phase 1 plan](docs/team/phase_01_data_backend.md) covers all defined
relational entities and controlled backend interfaces. Frontend delivery is included
behind a framework/location decision; no frontend or backend functionality exists yet.
These plans define future work beyond the partial P1 identity implementation, not
completed product capabilities or new business rules.

Single domain ownership, ORM-controlled relational schema, derived AI indexes,
separate interactive/background orchestration, explicit action confirmation and
candidate validation guide future implementation. Python 3.12, English docs and
uv are the agreed team defaults.

Consult [open questions](docs/architecture/open_questions.md) before implementing
the concrete contracts left open by the approved Phase 1 directions: department
semantics, scoped uniqueness and deletion rules, enum/scale values, distance and
preference cardinality, CV numbering, application transitions, source deduplication,
training assessment, AI guidance scope, reporting, providers and retention/visibility.
The register distinguishes approved direction from missing concrete definitions and
must not be treated as permission to invent acceptance criteria.
