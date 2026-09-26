# AI architecture

Sources: [DM](../../mahara_match_data_modeling.md) §§3.2, 4.B–E, 5 and
[PDF](../../Cahier%20de%20charge%20pr%C3%A9liminaire%20PDF.pdf) physical pp. 5, 7–10.

## Conversation and application actions

**User clarification (2026-09-20; Q22):** the ANETI employment advisor is the system
AI agent. It recommends jobs/training and helps correct or improve CVs. Its
reasoning belongs in ai/agents/, its orchestration in ai/workflows/, and reusable
CV capabilities in ai/document_intelligence/. It is not a human account role.
Assistant services own its conversation/execution history; candidates, matching
and training services own CV and recommendation state. The guidance folder is
only a scope marker, not another runtime or advisor-assignment module.

Support French, Arabic and Tunisian dialect. Responses use accessible internal
data, cite sources and explicitly identify absent information. Final hiring
decisions remain human (PDF pp. 2, 7).

LangGraph coordinates interactive steps, tools and human validation. The PDF's
example capabilities include extract_cv, search_jobs, compare_profile_with_job,
find_missing_skills, find_training, generate_cv, improve_cv,
get_company_information, draft_message and prepare_application. These are source
examples, not implemented tools or fixed Python interfaces.

Agent → tool → authorized application service → ORM. Reads and drafts need no
confirmation. Agent-initiated profile edits, applications, enrollments and external
sends require explicit user confirmation before execution, with idempotency keys.
Q15 still needs exact lifecycle states and replay/expiry rules. Assistant records live in the backend;
no conversation tables belong in ai/. Tool inputs cannot bypass permissions.
Human validation here means candidate/user review and confirmation, not approval
by a human ANETI advisor. CV correction proposals do not silently overwrite
candidate data; raw extraction remains restricted until candidate review (Q08).

## Retrieval and recommendations

Lexical, vector and graph retrieval are separate adapters combined by hybrid
retrieval, followed by reranking. RAG builds answers from retrieved evidence;
GraphRAG enriches that evidence with projected relationships. Explanations identify
matched skills, missing skills, offer requirements and supporting sources.

Vector and graph access must respect the caller's authorized data scope. Canonical
relational access goes through business services. Persistent offer-match results
belong to matching; training recommendations belong to training. Business services
validate and persist returned results without giving models write access.

The PostgreSQL-first baseline is a pilot. Q02 requires demonstrated and evaluated
Phase 7 hybrid plus graph/GraphRAG before a release is called MVP. Start search
with PostgreSQL text search and evaluate pgvector for semantic retrieval. Use
Neo4j only if the agreed graph traversal genuinely needs it; graph context may
reuse authoritative relational relationships.

## Document intelligence

Reuse pipelines/document_processing/ for direct PDF text extraction and OCR of
scanned/image inputs. ai/document_intelligence/ reserves section/skill parsing,
ATS analysis and CV generation. The candidate domain owns CV versions and analysis
records; documents owns file metadata. Restricted raw extraction can be retained
for review, but only candidate-approved facts enter normalized candidate data.
Retention of raw results remains part of Q19.

## Providers and evaluation

llm/providers/ and llm/prompts/ reserve provider adapters and prompts. Qwen is a
discussed candidate, not a selected dependency. Select LLM, embedding model and
reranker after French/Arabic/Tunisian, latency and hardware evaluation. Neo4j is
conditional on graph traversal need; LangGraph is planned but not installed.

evaluation/ reserves source-grounding, retrieval relevance, explanatory quality,
FR/AR/Tunisian understanding, latency and correct tool/confirmation behavior.
No datasets, scores, thresholds or evaluation code are fabricated. Fine-tuning
and quantization depend on suitable data/resources and evaluation (PDF p. 10).
