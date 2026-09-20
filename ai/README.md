# AI capability boundaries

All directories are reserved; no providers, agents, algorithms or workflows exist.

The ANETI employment advisor is the system's AI agent for recommendations and CV
corrections/improvements (user clarification, 2026-09-20; Q22). Its future execution
lives here; it is not a human advisor account or staffing workflow.

| Directory | Future responsibility |
| --- | --- |
| `agents/` | System AI agents, including the ANETI employment advisor |
| `workflows/` | LangGraph interactive orchestration and human validation |
| `tools/` | Agent-facing adapters to authorized application services |
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
Reusable AI capabilities return results for owning services to validate/persist.
They must not import business models or call back into their invoking services.

See [AI architecture](../docs/ai/architecture.md).
