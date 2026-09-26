# Architecture overview

## Authority and scope

Business sources: [DM](../../mahara_match_data_modeling.md) and
[PDF](../../Cahier%20de%20charge%20pr%C3%A9liminaire%20PDF.pdf).
PDF page references include the cover. This repository is a scaffold only.

**Source requirements:** PostgreSQL is authoritative, files live in object storage,
any vector/graph data is derived, interactive AI uses tools and user confirmation,
and background data work is orchestrated separately (DM §§1, 5; PDF pp. 9–10).

**Task decisions:** Django/DRF, Django ORM migrations, a modular monolith, English
documentation, Python 3.12, uv and the development tooling. The task explicitly
overrides the microservices wording in PDF p. 10; see Q01 in the question register.

**User clarification (2026-09-20):** the ANETI employment advisor is the system AI
agent for recommendations and CV assistance, not a human account role. Q22 records
this correction and the conflicting source wording. Execution belongs in ai/;
interaction history belongs in assistant; business state keeps its existing owners.

## Dependency paths

```text
API → Application service → Django ORM → PostgreSQL
Agent / LangGraph → Tool → Application service → Django ORM
Dagster → Reusable pipeline processing → Application service → Django ORM
Application service → AI capability → Returned result → Service validation/persistence
PostgreSQL validated data → Idempotent synchronization → Derived vector/graph index if needed
```

These are behavioral boundaries, not implemented interfaces. Services own business
validation, permissions and coordination. Cross-domain mutations use the owning
domain's services. Future ORM relationships may reference another domain's models
without transferring ownership; do not duplicate entities for convenience.

Tool adapters may depend on application services. Reusable AI capabilities must
not depend back on those services or ORM models. Interactive workflows coordinate
calls through tools; backend services must not import the agent orchestration layer.

## Subsystems

Business modules own relational state; common helpers remain domain-neutral.
`assistant` owns histories, while `ai/` owns execution and retrieval capabilities.
`imports` owns provenance, while `pipelines/` owns processing and orchestration.
Document metadata, CV versions and document bytes have distinct owners.

See [domain boundaries](domain_boundaries.md),
[persistence](../database/persistence_strategy.md),
[AI](../ai/architecture.md), and [workflows](../workflows/orchestration.md).

Infrastructure folders reserve operational concerns only. Heavy workloads may
later run in separate processes while keeping the same modular application and
schema ownership. There are no service APIs between new microservices here.

## Decisions still open

[The question register](open_questions.md) records source conflicts and omissions.
The 2026-09-25 decisions make the PostgreSQL baseline a pilot and require evaluated
Phase 7 hybrid plus graph/GraphRAG before the MVP label. React/TypeScript/Vite is
selected for the future `frontend/`; no frontend implementation is included here.
Provider/model selection and remaining domain contracts are listed in the question
register. Community and advanced integrations are post-MVP; freelance, fine-tuning
and quantization retain separate future gates.
