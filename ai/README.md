# AI capability boundaries

The ANETI candidate agent has a V1 job-matching workflow; other AI capabilities remain reserved.

The ANETI employment advisor is the system's AI agent for recommendations and CV
corrections/improvements (user clarification, 2026-09-20; Q22). Its future execution
lives here; it is not a human advisor account or staffing workflow.

| Directory | Future responsibility |
| --- | --- |
| `agents/` | System AI agents, including the ANETI employment advisor |
| `workflows/` | LangGraph orchestration; V1 retrieves candidate job matches and explains them |
| `tools/` | Agent-facing adapters to authorized application services; no direct database access |
| `document_intelligence/` | Parsing, ATS analysis and CV generation capabilities |
| `rag/` | Answers grounded in retrieved internal sources |
| `graphrag/` | Graph-enriched context and explanations |
| `retrieval/` | Lexical, vector, graph and hybrid retrieval adapters |
| `embeddings/` | Reusable embedding capability, not recurring job definitions |
| `reranking/` | Reordering retrieved results |
| `llm/` | Provider adapters and prompts |
| `evaluation/` | Future quality, grounding, language and action evaluations |

Agent → tool → application service → ORM. Agents and tools must not import models
or connect directly to relational storage. Retrieval adapters may access derived
indexes within authorization constraints; relational reads go through services.
The V1 matching tool calls the matching application service, which persists versioned
skill-coverage scores. The LLM explains only that persisted score and its evidence.
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
