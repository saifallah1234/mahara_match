# matching

**Responsibility:** Matching application services and persisted offer recommendations.

**Logical entity ownership:** `offer_matches`; derived `embeddings` index.

**Sources:** DM §4.C; PDF pp. 5, 9. DM means the root data model; PDF page numbers include the cover. See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Own business-facing comparison/recommendation coordination and offer-match results. AI retrieval/scoring capabilities return results through services. Training owns training_recommendations; never duplicate them here.

## Current backend

`OfferMatch` stores versioned scores and exposes scoped read-only results. A candidate sees their own results. Verified recruiters see results for applicants to their organization's offers; the API does not expose pre-application profile or CV data through match explanations.

The candidate agent's V1 calculator persists a deterministic `skill-coverage-v1` score: matched canonical skills divided by all skills attached to a published offer. Experience and location remain unknown, and a candidate with no recorded skills receives no scored matches. This is a narrow pilot baseline, not a final Q26 eligibility or ranking policy. Cross-domain reads use owning services.

`Embedding` stores derived vectors by entity type, entity UUID, and model name. Its vectors do not replace canonical records owned by candidate, recruitment, training, or identity domains.

## Production retrieval (2026-10-15)

`services/retrieval.py` holds the actor-scoped database legs used by the ANETI agent. Each builder returns a `ScopedSearch` (documents, vector neighbours, graph ranking) limited to what the owning domain says the actor may see; `ai/retrieval/hybrid/retriever.py` fuses the legs with RRF (k=60).

| Builder | Actor | Scope (from the owning service) |
|---|---|---|
| `candidate_offer_search` | candidate | published offers of verified, live organizations (`recruitment.services.retrieval_scope.visible_offers`); the candidate's own skills seed the graph |
| `recruiter_offer_search` | verified recruiter | every live offer of their organizations, drafts included |
| `recruiter_profile_search` | verified recruiter | `RECRUITERS` and `PUBLIC` profiles (Q28) through `candidates.services.discovery.list_candidates`, limited Q19 text only |
| `catalogue_search` | none (evaluation) | published offers and active programs, no personalisation |

- **Pre-filter, not post-filter.** The vector leg queries `embeddings WHERE entity_type = … AND entity_id IN (visible IDs)`. Nothing scope-related is stored with the vectors, so a profile switched to `PRIVATE` or an offer closed after indexing disappears at query time.
- **Graph leg.** Skills named in the question outrank profile/offer seed skills, which only break ties. Links are read through the owning domains' scope services (`offer_ids_for_skills`, `program_ids_for_skills`, `profile_ids_for_skills`), never other domains' models.
- **Other roles.** Training managers, ministry and admin are refused (`DomainPermissionError`). Adding one means a scope service in the owning domain, a builder here and a route in `ai/agents/intents.py`.
- Results are not persisted as `OfferMatch`; `skill-coverage-v1` keeps its meaning.

## Isolated evaluation dataset

Run commands from the repository root in Windows PowerShell. Development settings load `.env` and accept `DATABASE_URL`; do not pass `--settings`. These commands target the isolated `eval_graphrag` schema and do not write to `public`.

Preview schema creation/migrations, then confirm:

```powershell
uv run python backend/manage.py prepare_eval_schema --dry-run
uv run python backend/manage.py prepare_eval_schema --confirm eval_graphrag
```

Preview the source and expected row counts:

```powershell
uv run python backend/manage.py populate_eval_schema --dry-run
```

Extraction uses a controlled technical-skill vocabulary with Unicode and accent normalization. A skill is retained only if it appears in at least two descriptions. Each offer is linked to every retained skill it mentions; there is no per-offer cap or alphabetical truncation. The dry-run prints per-skill offer counts and the actual number of `offer_skills` rows. The dataset includes six synthetic programs, two skills each, leaving two or three retained skills without training coverage.

### Replace test data

`--replace` clears only EVAL-marked records in `eval_graphrag` and repopulates them in one transaction; it does not rerun migrations or touch `public`. It also deletes embeddings for those EVAL entity IDs. Preview, then explicitly confirm:

```powershell
uv run python backend/manage.py populate_eval_schema --replace --dry-run
uv run python backend/manage.py populate_eval_schema --replace --confirm eval_graphrag
```

After a successful replace, vectors must be recalculated because the purge removes them:

```powershell
uv run python backend/manage.py index_retrieval --schema eval_graphrag --model bge-m3 --base-url http://localhost:11434
```

## Retrieval index

`index_retrieval` embeds what may be retrieved: live offers of verified organizations (drafts included, for their recruiters), canonical skills, active programs of verified providers and opted-in limited candidate profiles. `--model` and `--base-url` default to `EMBEDDING_MODEL` (bge-m3) and `OLLAMA_BASE_URL`; the vector size must equal `EMBEDDING_DIMENSIONS` (1024) or the command fails.

`--prune` deletes this model's vectors whose entity is no longer indexable (deleted or unverified offers, archived programs, profiles switched to private). It is on by default for `--schema public` and off for `eval_graphrag`, and it refuses `--limit`. Vectors of other models are never touched. `--dry-run` calls Ollama and lists both upserts and deletions without writing.

The application schema (shared database; preview first, run only with approval):

```powershell
uv run python backend/manage.py index_retrieval --schema public --dry-run
uv run python backend/manage.py index_retrieval --schema public
```

First run on 2026-10-15 (approved): 1 offer and 1 skill re-indexed (the two pre-existing `bge-m3` rows), 0 programs, 0 opted-in profiles, 0 deletions. The 35 DRAFT offers of PENDING organizations in `public` are not indexed. The command is designed to be wrapped by a Dagster schedule later; no schedule exists yet.

The isolated evaluation schema. `--limit` applies separately to each entity type:

```powershell
uv run python backend/manage.py index_retrieval --schema eval_graphrag --model bge-m3 --base-url http://localhost:11434 --limit 3 --dry-run
uv run python backend/manage.py index_retrieval --schema eval_graphrag --model bge-m3 --base-url http://localhost:11434
```

Check vector counts in the Supabase SQL editor with this read-only query:

```sql
SELECT entity_type, count(*) AS vectors
FROM eval_graphrag.embeddings
WHERE model_name = 'bge-m3'
GROUP BY entity_type
ORDER BY entity_type;
```

## Retrieval evaluation

The root `retrieval_cases.py` has 24 FR/AR cases (12 French questions and their 12 Arabic translations; categories `keywords`, `semantic` and `multi_hop`, 8 each) with `relevant` labels over the 29 documents of the isolated dataset (23 offers and 6 training programs). The commands validate this file strictly: exactly 24 cases, matching `fr_`/`ar_` pairs with identical labels. The evaluator reads cases as UTF-8 and writes JSON as UTF-8. Hybrid modes compute all question vectors in batches before opening database queries. Ollama and transient PostgreSQL connection cuts are retried with exponential backoff; progress is printed. `--batch-size`, `--retries`, and `--retry-backoff` tune these behaviors.

Each mode writes a separate local candidate file:

```powershell
uv run python backend/manage.py evaluate_retrieval --schema eval_graphrag --cases retrieval_cases.py --mode baseline --output candidates-baseline.json
uv run python backend/manage.py evaluate_retrieval --schema eval_graphrag --cases retrieval_cases.py --mode hybrid --model bge-m3 --base-url http://localhost:11434 --output candidates-hybrid.json
uv run python backend/manage.py evaluate_retrieval --schema eval_graphrag --cases retrieval_cases.py --mode hybrid_graph --model bge-m3 --base-url http://localhost:11434 --output candidates-hybrid-graph.json
```

The evaluator runs the production retrieval code: `ai.retrieval.hybrid.retriever.retrieve` over `matching.services.retrieval.catalogue_search`, the public-catalogue scope (published offers of verified organizations and active programs, no actor personalisation). Each mode selects which legs run. `--model` and `--base-url` default to `EMBEDDING_MODEL` and `OLLAMA_BASE_URL`.

Mode definitions. Only offers and training programs are retrieved; `--top-k` (default 10) sets the candidates kept per question.

- `baseline`: token-overlap ranking (`ai/retrieval/lexical/scoring.py`), not BM25. It counts the distinct question terms found in each document after case and accent folding, Arabic normalisation (tashkeel and tatweel removed, alef forms unified) and a small FR/AR/EN stop-word list. Terms have two characters or more; Latin and Arabic runs are split (`وSQL` gives `sql`); a slash compound keeps its whole form and its parts (`CI/CD` gives `ci/cd`, `ci`, `cd`). **Documents sharing no term are excluded.** There is no stemming or IDF weighting. Ties are broken by entity type, then UUID.
- `hybrid`: the baseline ranking fused with a pgvector cosine ranking (top `--top-k` only, pre-filtered to the scope's IDs) by reciprocal rank fusion (k=60).
- `hybrid_graph`: `hybrid` plus a third ranking from the skill graph. Canonical skills named in the question (case-insensitive whole term; boundaries consider Latin letters and digits only) select the offers and training programs linked to them, ordered by the number of matched skills. It is a minimal relational graph over existing tables, not a graph database. There is no reranker.

## Metrics

`compute_retrieval_metrics` reads the three candidate files and the labels in `retrieval_cases.py`. It does not query the database or Ollama. It prints one Markdown table per mode (global, per category, per language) to the console and writes per-case metrics as UTF-8 JSON (default `metrics-retrieval.json`):

```powershell
uv run python backend/manage.py compute_retrieval_metrics
```

Metrics use binary relevance over the candidates kept per mode (top 10): MRR, Recall@5, Recall@10, NDCG@3 and NDCG@5. For the six "absence" cases (`fr_`/`ar_` `keywords_03`, `multi_hop_01` and `multi_hop_03`; the skills PostgreSQL and Apache Spark have no training program), training programs are removed from both the ranking and the relevant set before scoring, so only offers are scored. This removal happens after the top-10 cut.

`check_relevant_labels` is a read-only check of the labels against the skill links in `eval_graphrag`:

```powershell
uv run python backend/manage.py check_relevant_labels --schema eval_graphrag
```

It confirms that the label file follows the written relevance rules. It does not prove that the rules themselves are right.

## Results (24 cases, local run)

Values rounded to three decimals. The candidate and metrics files are git-ignored; rerun the commands above to reproduce them. Run on 2026-10-15 with the production retrieval modules; the previous column comes from the Phase 7 evaluation code (reproduced exactly on the same date before comparing).

| Mode | MRR | Recall@5 | Recall@10 | NDCG@3 | NDCG@5 |
|---|---:|---:|---:|---:|---:|
| baseline | 0.714 | 0.325 | 0.491 | 0.613 | 0.608 |
| hybrid | 0.873 | 0.414 | 0.594 | 0.753 | 0.742 |
| hybrid_graph | 0.915 | 0.493 | 0.701 | 0.814 | 0.819 |

Previous (Phase 7 lexical leg, zero-overlap documents kept):

| Mode | MRR | Recall@5 | Recall@10 | NDCG@3 | NDCG@5 |
|---|---:|---:|---:|---:|---:|
| baseline | 0.789 | 0.357 | 0.524 | 0.625 | 0.633 |
| hybrid | 0.758 | 0.315 | 0.478 | 0.640 | 0.615 |
| hybrid_graph | 0.883 | 0.509 | 0.698 | 0.816 | 0.810 |

NDCG@5 by group:

| Group | baseline | hybrid | hybrid_graph |
|---|---:|---:|---:|
| keywords | 0.863 | 0.923 | 0.979 |
| semantic | 0.171 | 0.545 | 0.545 |
| multi_hop | 0.790 | 0.758 | 0.935 |
| fr | 0.560 | 0.659 | 0.803 |
| ar | 0.656 | 0.825 | 0.835 |

What changed and why:

- The old lexical leg returned every document, including those sharing no term with the question, in UUID order. The four Arabic `semantic` questions share no term with the French/English documents, so their old baseline "hits" were UUID-order luck (confirmed per case). They now return nothing, which is why the baseline drops on `semantic` (0.400 to 0.171) and in Arabic, while `keywords` and `multi_hop` improve with accent folding and stop words.
- `hybrid` improves most (NDCG@5 0.615 to 0.742): RRF no longer gives points to arbitrary zero-overlap documents, so the vector ranking decides the semantic questions.
- `hybrid_graph` improves on MRR, Recall@10 and NDCG@5 but loses 0.016 Recall@5 and 0.003 NDCG@3. The per-case comparison traces this to `ar_semantic_02` and `ar_semantic_04`, where the old lucky lexical order put a relevant offer first; the vector ranking alone now decides them.

Vector search helps on the semantic (paraphrase) questions. The graph helps where a skill is named (keywords, multi_hop) and changes nothing on the semantic questions, which name no skill. Alone, `hybrid` is below the baseline on multi_hop, probably because it ranks training programs high and these are removed for the absence cases (not verified).

## Evaluation limits

These numbers show that the mechanism works on a small synthetic dataset. They are not evidence of better retrieval on real data.

- The 6 training programs and their sessions are synthetic (`TEST ONLY`), and the skill-to-program groupings are arbitrary (for example the Docker program also covers Machine Learning). The 15 skills were extracted from offer descriptions by keywords. 22 of the 23 offers are DRAFT in `public` and are published only inside `eval_graphrag`.
- The questions were written from these groupings, and relevance is defined by the same offer-skill-program links that `hybrid_graph` traverses. That mode is therefore favored by construction, mostly on `keywords` and `multi_hop`.
- There are about 12 distinct questions (each Arabic question translates a French one) over 29 documents. Only the top 10 candidates are kept per mode while some questions have 17 to 22 relevant documents, so Recall@10 is capped: prefer MRR and NDCG@3/5. No difference is statistically solid.
- Labels were produced by an AI assistant from written rules and checked automatically; only part of them were reviewed by a human. Ambiguous cases: `semantic_01` (two offers that mention PostgreSQL but not SQL are not marked relevant), `semantic_04` (read as JavaScript AND Cloud Computing), the absence cases above, and `multi_hop_02`/`multi_hop_04` (all six programs are relevant, so they do not discriminate; `multi_hop_04` has 22 relevant documents out of 29).
- The lexical baseline is a token overlap, not BM25. The semantic list is cut to the top 10 while the lexical and graph rankings are not. The RRF constant (k=60) is not tuned. There is no reranker. The vector column has no fixed dimension, so there is no HNSW or IVFFlat index. Skill-to-skill edges are not implemented.
- There is no answer-generation step in the evaluation, so "information absent" behavior is not measured. The production agent tools (`ai/tools/job_search.py`, `ai/tools/candidate_search.py`) use the same retrieval code but are not part of these metrics.

## Labeling and cleanup

Generate the neutral sheet from the three candidate files; this reads `eval_graphrag` and writes only the local UTF-8 Markdown file:

```powershell
uv run python backend/manage.py create_labeling_sheet
```

To remove the isolated schema, preview first and provide its name as explicit confirmation:

```powershell
uv run python backend/manage.py cleanup_eval_schema --dry-run
uv run python backend/manage.py cleanup_eval_schema --confirm-schema eval_graphrag
```
