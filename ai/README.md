# AI capability boundaries

The ANETI agent serves candidates (job search with training suggestions) and verified recruiters (opted-in profile search, own-offer search) through scoped hybrid retrieval; other AI capabilities remain reserved.

The ANETI employment advisor is the system's AI agent for recommendations and CV
corrections/improvements (user clarification, 2026-09-20; Q22). Its future execution
lives here; it is not a human advisor account or staffing workflow.

| Directory | Future responsibility |
| --- | --- |
| `agents/` | ANETI agent: `intents.py` (EN/FR/AR role-aware routing), `templates.py` (deterministic replies), `anetai.py` (routes, grounding check, trace allow-list), `service.py` (run + history) |
| `workflows/` | LangGraph orchestration: `job_matching.py` runs any route's tool then its explainer |
| `tools/` | Agent-facing adapters to authorized application services: `job_search.py` (candidate), `candidate_search.py` (recruiter), `job_matches.py` (Phase 7 baseline, rollback only) |
| `document_intelligence/` | `parsing/cv_reader.py` (PDF/DOCX text, format risks, sections, contacts), `parsing/section_extraction.py` (per-section entries from the local chat model, validated against the source text, line-split fallback) and `ats/analysis.py` (deterministic ATS readiness and role fit against the YAML role profiles in `ats/roles/` and level table `ats/levels.yaml`) and `ats/rewrite.py` (one-bullet rewrites and summary proposals, validated against the CV's facts, rule-based fallback) and `generation/cv_writer.py` (the CV draft as an ATS-friendly DOCX or PDF, written with python-docx and PyMuPDF) |
| `rag/` | Answers grounded in retrieved internal sources |
| `graphrag/` | `missing_skill_training.py`: missing skills → active training programs |
| `retrieval/` | `lexical/scoring.py` (FR/AR/EN token overlap, zero-overlap excluded), `hybrid/retriever.py` (legs + RRF, degrades without vectors); scoped database legs live in `backend/apps/matching/services/retrieval.py` |
| `embeddings/` | Reusable embedding capability, not recurring job definitions |
| `reranking/` | Reordering retrieved results |
| `llm/` | Provider adapters and prompts; `providers/embeddings.py` is the Ollama embedding client (`EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `OLLAMA_BASE_URL`) |
| `evaluation/` | Future quality, grounding, language and action evaluations |

Agent → tool → application service → ORM. Agents and tools must not import models
or connect directly to relational storage. Retrieval adapters may access derived
indexes within authorization constraints; relational reads go through services.
Retrieval tools get documents, vector neighbours and graph links only through
actor-scoped backend services; vectors are pre-filtered by visible IDs. Results are
explained from evidence (matched/missing skills, training suggestions) and are not
persisted as offer matches. The Phase 7 skill-coverage tool remains selectable with
`ANETAI_CANDIDATE_TOOL=baseline` until the retrieval route is verified live.
Other capabilities return results for owning services to validate/persist.

See [AI architecture](../docs/ai/architecture.md).

## Repeatable Ollama check

The mocked suite is the default. To exercise the job-matching graph against the
real local model, set `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in the project `.env`
(or export them in the shell that launches pytest), then run:

```sh
RUN_OLLAMA_TESTS=1 uv run --frozen pytest -m ollama tests/integration/ai/test_ollama_job_matching.py -q
```

The test uses synthetic evidence and does not connect to the application database.
When Ollama runs on Windows and Django runs in WSL, set `OLLAMA_BASE_URL` to the
Windows host address reachable from WSL, for example `http://172.20.144.1:11434`.

## Document intelligence dependencies (ATS analysis, 2026-11-06)

- `pymupdf` (<2): read PDF text, fonts, images and tables, and detect scans; 2.x pulls in onnxruntime.
- `python-docx`: read DOCX CVs (and later write the generated DOCX).
- `pyyaml` (+ `types-pyyaml` for mypy): load the versioned role profiles and level table.
- `rapidfuzz`: fuzzy matching of section headings and skill aliases.
