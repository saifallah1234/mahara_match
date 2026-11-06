# Plan: role-scoped hybrid + graph retrieval for the ANETI agent

Status: agreed on 2026-10-15, not yet implemented.
Branch base: `feature/frontend-apis` at `2256838` (PR #11 merged).

## 1. Problem

Phase 7 delivered an evaluation harness for retrieval, not a production feature.
The open problems:

1. **The agent doesn't use it.** `ai/tools/job_matches.py` calls `skill-coverage-v1`
   (`backend/apps/matching/services/baseline.py`). `ai/retrieval/*`, `ai/rag/` and
   `ai/graphrag/` are empty.
2. **The graph leg has no scope.** `graph_skill_ranking` reads `OfferSkill`,
   `TrainingSkill` and `Skill` directly. It has no published or not-deleted filter, no
   `actor`, and no owning-service call. On `public` it would return DRAFT, closed,
   deleted or unverified-organization offers. This breaks the AI architecture doc
   ("respect the caller's authorized data scope") and AGENT.md rule 5.
3. **The keyword ranking includes non-matches.** `lexical_ranking` returns documents
   with zero overlap. Reciprocal rank fusion then gives every one of them points in
   arbitrary UUID order.
4. **The embedding client is in the wrong place.** It is a static method on a
   management command (`index_retrieval.Command._embed`), reused by `evaluate_retrieval`.
   The 1024 vector size is hard-coded while the model name is a parameter.
5. **Nothing indexes `public`.** Only `eval_graphrag.embeddings` (44 vectors) exists.
   `public.embeddings` holds 2 rows of unknown origin.
6. **The agent is candidate-only and English-only.** `AgentRunView` calls
   `own_profile(actor)`. `is_job_match_request` only matches English phrases.

## 2. Decisions (from the interview)

| Topic | Decision |
|---|---|
| Roles this iteration | **Candidate + recruiter.** The training manager, ministry and admin scopes are out of scope, with the extension point documented. |
| Placement | **Split.** Scoped database legs are backend services that take `actor`. Embedding provider, lexical scoring, fusion, tools and workflow go in `ai/`. |
| Scope filtering | **Pre-filter.** Owning services return visible IDs. pgvector searches `WHERE entity_id IN (scope)`. No scope copies in `embeddings`. |
| Freshness | **Command + stale check.** `index_retrieval --schema public` upserts indexable items and deletes vectors that are no longer indexable. The query-time scope still hides anything stale. |
| Recruiter can retrieve | Their own organization's offers, **including drafts**, and **opted-in candidate limited profiles** (Q19 fields only). **Not** applicants' CVs. |
| Recruiter access | Agent chat, opened to recruiters with recruiter intents and tool. |
| Dual candidate + recruiter role | Assumed impossible. Route by the user's single role and reject anything that doesn't match it. |
| Language | Retrieval and intent routing accept EN/FR/AR. Replies use **a deterministic template in the request language**. English templates may still be reworded by the LLM under the existing grounding check. A grounding redesign is deferred. |
| Ollama down | **Degrade** to lexical + graph and record `vector_unavailable` in the tool-call trace. |
| Candidate query | Question text plus the candidate's **own profile skills**. The skills seed the graph leg, so a vague request still gets personalised results. |
| Explanation | **Retrieve, then explain.** Retrieval picks and orders offers. Matched and missing skills against the candidate profile are the cited explanation. Results are **not** persisted as `OfferMatch`. |
| Training | For each returned offer, graph-hop **missing skills → active programs** that teach them. These are suggestions, never enrollments. |
| Keyword ranking | Drop zero-overlap documents. Add case and accent folding, with Arabic normalisation (see 4.2), and a small FR/AR/EN stop-word list. No PostgreSQL FTS. |
| Recruiter query | A free question, or "candidates for offer X", where X's text and skills become the query. X is allowed only if it's in the recruiter's scope. |
| Trace privacy | The tool trace stores **IDs, ranks, scores and matched skill names only**. Limited-profile text is fetched live for display and never copied into assistant history. |
| Evaluation | `evaluate_retrieval` calls the **production** modules with a public-catalogue scope. Re-run it and update the README tables. |
| Result size | **5** offers or profiles. Up to **2** training programs per offer. |

## 3. Target architecture

```
AgentRunView (candidate or recruiter)
  └─ ai/agents/service.start_agent_run(actor, prompt)
       └─ ai/agents/anetai: route by role + intent (EN/FR/AR)
            └─ ai/workflows/job_matching.py (LangGraph)
                 ├─ candidate: ai/tools/job_search.search_jobs_for_candidate(actor, question)
                 └─ recruiter: ai/tools/candidate_search.search_candidates / search_own_offers
                      └─ ai/retrieval/hybrid.py  (lexical + vector + graph → RRF)
                           ├─ ai/llm/providers/embeddings.py  (Ollama bge-m3, degrade on failure)
                           └─ backend/apps/matching/services/retrieval.py  (actor-scoped DB legs)
                                ├─ recruitment.services.retrieval_scope   (visible offer IDs/docs)
                                ├─ training.services.retrieval_scope      (visible program IDs/docs)
                                └─ candidates.services.retrieval_scope    (own skills; opted-in profiles)
```

Rules that apply everywhere:
- Code in `ai/` **never** imports Django models. It calls backend services only.
- Every backend function takes `actor` and gets visibility from the owning domain's service.
- Documents come back as plain dataclasses (`RetrievalDocument(entity_type, entity_id, text, title)`),
  never querysets.

## 4. Files to change

### 4.1 Owning-domain scope services (new)

Each of these returns IDs and/or document text, and each one reuses the domain's
existing visibility rules.

- `backend/apps/recruitment/services/retrieval_scope.py`
  - `visible_offer_ids(actor) -> QuerySet[UUID]`
    - **Candidate:** the published, non-deleted, verified-organization filter from `list_indexable_job_offers()`.
    - **Recruiter:** `list_job_offers(actor)`, so their organization's offers including drafts, and nothing deleted.
  - `offer_documents(offer_ids) -> list[RetrievalDocument]`. This moves the text-building code out of `embedding_index.py`.
  - `offer_ids_for_skills(actor, skill_ids) -> Counter[UUID]`. This is the scoped replacement for the
    `OfferSkill` loop in `graph_skill_ranking`.
  - `offer_skill_names(actor, offer_id)`. Used for the matched/missing explanation and for the
    "candidates for offer X" query. Raises `DomainNotFoundError` when X is out of scope.
- `backend/apps/training/services/retrieval_scope.py`
  - `visible_program_ids()`. Based on `list_indexable_programs()`: active programs at verified, non-deleted providers.
  - `program_documents(ids)`.
  - `programs_teaching(skill_ids, limit_per_skill)`. Used for the missing-skill hop.
- `backend/apps/candidates/services/retrieval_scope.py`
  - `own_skill_ids(actor)`. Built on `list_records(actor, CandidateSkill)`.
  - `discoverable_profile_ids(actor)`. Built on `list_candidates(actor)`, which already enforces the
    recruiter role, the verified company and `profile_visibility=RECRUITERS`.
  - `limited_profile_documents(ids)`. Uses **only** the Q19 fields: headline, skills, experience
    titles, education level, governorate, work preferences. Never name, contact, birth date or CV.
  - `limited_profile_view(actor, ids)`. Fetches the live display fields for the reply.

### 4.2 Matching (backend)

- `backend/apps/matching/services/retrieval.py` (new). Holds the actor-scoped database legs:
  - `semantic_ranking(actor_scope, vector, model_name, entity_types, limit)` with the pgvector
    `WHERE entity_type IN … AND entity_id IN (scope)` pre-filter.
  - `graph_ranking(actor, seed_skill_ids, target)`. Calls the scope services above, never other domains' models.
  - `skills_mentioned(question)`. Moved from `skill_is_mentioned`, reading skills through the taxonomy
    `skills()` service.
- `backend/apps/matching/services/evaluation_retrieval.py`
  - Remove `lexical_ranking`, `semantic_ranking`, `graph_skill_ranking`, `reciprocal_rank_fusion`
    and `skill_is_mentioned`. They move to the production modules.
  - Keep `candidate_details` and `relevance_metrics`.
  - Remove the direct `OfferSkill`, `TrainingSkill` and `Skill` imports.
- `backend/apps/matching/services/embedding_index.py`
  - Build documents from the scope services.
  - Add `candidate_profile` documents for opted-in profiles.
  - Add `delete_stale_embeddings(model_name, keep: dict[entity_type, set[UUID]]) -> int`.
- `backend/apps/matching/management/commands/index_retrieval.py`
  - Accept `--schema public|eval_graphrag`.
  - Use the new embedding provider.
  - Add `--prune`. It defaults to on for `public` and reports deletions. `--dry-run` previews both upserts and deletions.
  - Use the dimension from the provider config, not a literal `1024`.
- `backend/apps/matching/management/commands/evaluate_retrieval.py`
  - Call `ai/retrieval/hybrid.py` with a "public catalogue" scope (published offers + active programs, no actor personalisation).
  - Drop the import of `IndexCommand._embed`.

### 4.3 AI layer

- `ai/llm/providers/embeddings.py` (new)
  - `embed(texts) -> list[list[float]]`, configured by `EMBEDDING_MODEL` (default `bge-m3`),
    `EMBEDDING_DIMENSIONS` (default `1024`) and `OLLAMA_BASE_URL`.
  - Batching, timeout and the existing transient-retry rule.
  - Raises a typed `EmbeddingUnavailable` error.
  - Add the variables to `.env.example`.
- `ai/retrieval/lexical/scoring.py` (new). Token overlap with these changes:
  - casefold;
  - NFKD accent stripping (`données` → `donnees`);
  - Arabic normalisation (strip tashkeel, unify alef forms);
  - a small FR/AR/EN stop-word list;
  - **documents with zero overlap are excluded.**
- `ai/retrieval/hybrid.py` (new)
  - `retrieve(scope_request) -> RetrievalResult`.
  - Runs lexical, vector and graph, then RRF with k=60.
  - Returns ranked keys plus per-leg ranks for the trace.
  - Sets `vector_unavailable=True` when it degrades.
- `ai/graphrag/missing_skill_training.py` (new). Offer → missing skills → up to 2 programs per offer.
- `ai/tools/job_search.py` (new). Candidate tool:
  - The question plus `own_skill_ids` are the graph seeds.
  - Top 5 offers with matched and missing skills and training suggestions.
  - Output holds IDs, titles, organization and skill names.
- `ai/tools/candidate_search.py` (new). Recruiter tools:
  - `search_candidates(actor, question, offer_id=None)` returns profile IDs, ranks and matched skill names.
  - `search_own_offers(actor, question)`.
- `ai/tools/job_matches.py`. Kept for the baseline route until the new path is verified, then removed in a follow-up.
- `ai/workflows/job_matching.py`. Add role-specific routes and the degraded-vector flag. Per-leg ranks and latency go into the tool call.
- `ai/agents/anetai.py`
  - Role-aware routing: candidate intents (jobs, jobs + training) and recruiter intents (find candidates, candidates for offer X, my offers).
  - EN/FR/AR keyword patterns.
  - Deterministic templates in EN/FR/AR.
  - The LLM rewords English replies only, under the existing `_stays_within_evidence` check. The check is extended to the new evidence shapes.
- `ai/agents/service.py`. Pass the role and route, and record the trace (privacy rule: IDs and scores only).

### 4.4 API

- `backend/apps/assistant/api/agent_run_views.py`
  - Replace the `own_profile(actor)` gate with "the actor is an active candidate **or** a verified recruiter".
  - Recruiters without a verified organization get the existing 403 domain error.
- The serializers are unchanged. Responses add nothing new, because the reply text and IDs already fit.

### 4.5 Docs (AGENT.md rule 10)

- `backend/apps/matching/README.md`: production retrieval, `--schema public`, prune behaviour, new eval numbers.
- `docs/ai/architecture.md` and `CONTEXT.md`: scoped retrieval, roles, degrade rule, trace privacy.
- `docs/architecture/open_questions.md`: new entries with sources. See section 6.
- `ai/README.md`: the new modules.

## 5. Out of scope

- Training manager, ministry (its KPIs and privacy contracts are open) and admin retrieval. Only the extension point is documented.
- Embedding or searching CV text, including applicants' submitted CVs.
- Persisting retrieval results as `OfferMatch` and changing the meaning of `skill-coverage-v1`.
- Redesigning the grounding check and LLM-written FR/AR replies.
- PostgreSQL full-text search or BM25, a reranker, an HNSW or IVFFlat index, skill-to-skill edges, Neo4j.
- Dagster scheduling of `index_retrieval` (the command is designed so it can be wrapped later).
- New `retrieval_cases.py` cases with candidate personalisation.
- Frontend changes beyond what the existing chat already renders.

## 6. Edge cases and how they're handled

| Case | Handling |
|---|---|
| Offer closed or deleted after indexing | The pre-filter excludes it at query time. The next `--prune` run deletes its vector. |
| Candidate switches to PRIVATE | `list_candidates` excludes the profile immediately. Prune deletes the vector. |
| Candidate profile with `PUBLIC` visibility | `list_candidates` currently returns `RECRUITERS` only, and we reuse that unchanged. Log it as an open question: should PUBLIC profiles also be discoverable? |
| Recruiter asks for "candidates for offer X" outside their organization | `offer_skill_names` raises not-found and the agent replies that the offer isn't accessible, without leaking that it exists. |
| Candidate with no skills plus a vague question | No graph seeds. Lexical + vector on the question. If the question has no content terms, reply with the existing "add skills to your profile" message. |
| Ollama down or timing out | Lexical + graph only. `vector_unavailable` goes in the trace. The reply is unchanged in form. |
| Model or dimension mismatch in stored vectors | The search filters by `model_name`. The indexer validates the configured dimension. A mismatch is a command error, not silent. |
| Unverified recruiter organization | `list_candidates` / `organization_ids_with_permission` raise, which becomes a permission error (no silent empty results). |
| Recruiter with an empty scope (no offers) | `search_own_offers` returns an empty result with a reason code. |
| `eval_graphrag` vs `public` | `use_schema` stays limited to commands. Runtime retrieval always uses the default connection (`public`). |
| The 2 unknown rows in `public.embeddings` | Inspect them before the first `--prune` run. `--dry-run` lists what would be deleted. |

## 7. Verification

### Static
`uv run --frozen ruff check .`, `ruff format --check .` and `mypy .` must all pass.

### Unit tests (`tests/unit/`)
- `ai/test_lexical_scoring.py`
  - Zero-overlap documents are excluded.
  - Accent folding (`données`/`donnees`).
  - Arabic normalisation.
  - Stop words are ignored.
  - `CI/CD`-style tokens behave as documented.
- `ai/test_hybrid_retrieval.py`
  - RRF ordering.
  - Degrade path when `EmbeddingUnavailable` is raised: lexical + graph only, with the flag set.
  - Per-leg ranks appear in the result.
- `ai/test_embeddings_provider.py`
  - Batching.
  - Retry on transient 5xx/429/URLError.
  - Dimension mismatch raises.
  - Env config is read.
- `ai/test_anetai_routing.py`
  - EN/FR/AR intents for each role.
  - A recruiter intent from a candidate is rejected, and the reverse.
  - Templates are produced in each language.
- `ai/test_job_search_tool.py` and `ai/test_candidate_search_tool.py` with fake services:
  - output shape;
  - 5 items and ≤2 trainings each;
  - **the trace contains no limited-profile text**.
- Update `backend/matching/test_graph_skill_matching.py` and `test_evaluation_workflow.py`
  for the moved functions. Existing metric tests must keep passing.

### Integration tests (`tests/integration/`, isolated `mahara_test_*` schema from `conftest.py`)
`matching/test_scoped_retrieval.py` covers the leak tests. These are the most important:
- A candidate never receives a DRAFT, CLOSED or deleted offer, or an offer from an unverified organization, from **any** leg (lexical, vector, graph). Vectors are seeded directly with fixed values.
- A recruiter receives their own organization's DRAFT offers but not another organization's.
- A recruiter receives only `RECRUITERS`-visibility profiles. A PRIVATE profile with a matching vector is never returned.
- An unverified recruiter gets a permission error.
- "Candidates for offer X" with X from another organization returns not-found.
- The missing-skill hop returns only ACTIVE programs from verified providers.
- `delete_stale_embeddings` removes vectors for items that are no longer indexable and keeps the rest.
- The tool-call `output_summary_json` for recruiter runs holds profile IDs and skill names only.

`assistant/`: the agent endpoint accepts verified recruiters and still rejects other roles.

### Live checks (manual; need confirmation before touching shared data)
1. `ollama pull bge-m3` on the Windows Ollama host.
2. Re-run the three `evaluate_retrieval` modes on `eval_graphrag` and `compute_retrieval_metrics`.
   - Expectation: `hybrid` improves over the current 0.615 NDCG@5 now that the zero-overlap noise is gone.
   - Expectation: `hybrid_graph` stays ≥ its current values (MRR 0.883, NDCG@5 0.810). It should be unchanged in principle, because every eval item is published.
   - Any regression is investigated before merging. Update the README tables either way.
3. `index_retrieval --schema public --dry-run`, review it (including the 2 existing rows), and only then run it for real. **This writes to the shared Supabase database, so it needs explicit approval.**
4. Through the agent endpoint, as a seeded candidate and as a seeded verified recruiter: one EN, FR and AR request each, and the Ollama-stopped degrade case.

## 8. Implementation order

1. Embedding provider + lexical fix + hybrid module (pure code, unit-tested).
2. Owning-domain scope services + matching `retrieval.py` + leak integration tests.
3. Switch the evaluation commands to the production modules, then re-run and compare the metrics.
4. Candidate tool and workflow route, plus the training hop.
5. Recruiter tools, routing and the API gate change.
6. Indexing `public` with prune (dry-run first, then wait for approval).
7. Docs and open questions. Final ruff/mypy/pytest run with the actual results reported.
