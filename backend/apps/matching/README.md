# matching

**Responsibility:** Matching application services and persisted offer recommendations.

**Logical entity ownership:** `offer_matches`; derived `embeddings` index.

**Sources:** DM §4.C; PDF pp. 5, 9. DM means the root data model; PDF page numbers include the cover. See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Own business-facing comparison/recommendation coordination and offer-match results. AI retrieval/scoring capabilities return results through services. Training owns training_recommendations; never duplicate them here.

## Current backend

`OfferMatch` stores versioned scores and exposes scoped read-only results. A candidate sees their own results. Verified recruiters see results for applicants to their organization's offers; the API does not expose pre-application profile or CV data through match explanations.

The candidate agent's V1 calculator persists a deterministic `skill-coverage-v1` score: matched canonical skills divided by all skills attached to a published offer. Experience and location remain unknown, and a candidate with no recorded skills receives no scored matches. This is a narrow pilot baseline, not a final Q26 eligibility or ranking policy. Cross-domain reads use owning services.

`Embedding` stores derived vectors by entity type, entity UUID, and model name. Its vectors do not replace canonical records owned by candidate, recruitment, training, or identity domains.

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

Index only `eval_graphrag`. `--limit` applies separately to each entity type; a dry-run calls Ollama but does not write vectors:

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

Mode definitions. Only offers and training programs are retrieved; `--top-k` (default 10) sets the candidates kept per question.

- `baseline`: token-overlap ranking, not BM25. It counts the distinct question tokens (three characters or more, case-folded) found in each document, with no accent folding, stemming, stop-word removal or IDF weighting. Ties are broken by entity type, then UUID, so tie order is arbitrary.
- `hybrid`: the baseline ranking fused with a pgvector cosine ranking (top `--top-k` only) by reciprocal rank fusion (k=60).
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

Values rounded to three decimals. The candidate and metrics files are git-ignored; rerun the commands above to reproduce them.

| Mode | MRR | Recall@5 | Recall@10 | NDCG@3 | NDCG@5 |
|---|---:|---:|---:|---:|---:|
| baseline | 0.789 | 0.357 | 0.524 | 0.625 | 0.633 |
| hybrid | 0.758 | 0.315 | 0.478 | 0.640 | 0.615 |
| hybrid_graph | 0.883 | 0.509 | 0.698 | 0.816 | 0.810 |

NDCG@5 by group:

| Group | baseline | hybrid | hybrid_graph |
|---|---:|---:|---:|
| keywords | 0.804 | 0.814 | 0.963 |
| semantic | 0.400 | 0.554 | 0.554 |
| multi_hop | 0.696 | 0.478 | 0.913 |
| fr | 0.515 | 0.619 | 0.772 |
| ar | 0.751 | 0.612 | 0.847 |

Vector search helps on the semantic (paraphrase) questions. The graph helps where a skill is named (keywords, multi_hop) and changes nothing on the semantic questions, which name no skill. Alone, `hybrid` is below the baseline on multi_hop, probably because it ranks training programs high and these are removed for the absence cases (not verified). The lexical baseline is strong in Arabic because skill names stay in Latin letters.

## Evaluation limits

These numbers show that the mechanism works on a small synthetic dataset. They are not evidence of better retrieval on real data.

- The 6 training programs and their sessions are synthetic (`TEST ONLY`), and the skill-to-program groupings are arbitrary (for example the Docker program also covers Machine Learning). The 15 skills were extracted from offer descriptions by keywords. 22 of the 23 offers are DRAFT in `public` and are published only inside `eval_graphrag`.
- The questions were written from these groupings, and relevance is defined by the same offer-skill-program links that `hybrid_graph` traverses. That mode is therefore favored by construction, mostly on `keywords` and `multi_hop`.
- There are about 12 distinct questions (each Arabic question translates a French one) over 29 documents. Only the top 10 candidates are kept per mode while some questions have 17 to 22 relevant documents, so Recall@10 is capped: prefer MRR and NDCG@3/5. No difference is statistically solid.
- Labels were produced by an AI assistant from written rules and checked automatically; only part of them were reviewed by a human. Ambiguous cases: `semantic_01` (two offers that mention PostgreSQL but not SQL are not marked relevant), `semantic_04` (read as JavaScript AND Cloud Computing), the absence cases above, and `multi_hop_02`/`multi_hop_04` (all six programs are relevant, so they do not discriminate; `multi_hop_04` has 22 relevant documents out of 29).
- The lexical baseline is a token overlap, not BM25, and `CI/CD` is never a token (three characters or more). The semantic list is cut to the top 10 while the lexical and graph rankings are not. The RRF constant (k=60) is not tuned. There is no reranker. The vector column has no fixed dimension, so there is no HNSW or IVFFlat index. Skill-to-skill edges are not implemented.
- There is no answer-generation step, so "information absent" behavior is not measured. There is no evidence pack and no LangGraph tool in `ai/`.

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
