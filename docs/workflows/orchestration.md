# Workflow and pipeline responsibilities

Sources: [DM](../../mahara_match_data_modeling.md) §§3.2–3.3, 4.B, 4.E–F, 5 and
[PDF](../../Cahier%20de%20charge%20pr%C3%A9liminaire%20PDF.pdf) physical pp. 9–10.

| Path | Future coordinator | Responsibility |
| --- | --- | --- |
| Interactive assistance | LangGraph under ai/workflows/ | ANETI AI advisor recommendations, CV assistance, tool selection, user validation and action preparation |
| Background data work | Dagster under pipelines/dagster/ | Recurrent ingestion, normalization, quality, embeddings and synchronization |
| Reusable processing | pipelines/ and ai/ capabilities | Processing independent of its scheduler |
| Business state | Backend application services | Authorization, domain validation and relational persistence |

## CV processing

The ANETI employment advisor is the system AI agent (user clarification,
2026-09-20; Q22). It can propose CV corrections/improvements and recommendations
through tools and owning application services. User review is candidate validation,
not a human advisor assignment or approval step. External-action confirmation
still applies; other mutation confirmation details remain open under Q15.

File metadata/URI → direct text extraction or OCR → NLP/LLM parsing → candidate
review/correction → validated structured profile. Technical processing must not
silently overwrite candidate data. Retaining unconfirmed raw results requires Q08
to be resolved. Generation and ATS evaluation return results to candidate services.

## Imports and synchronization

Authorized source → import batch → row processing/normalization/quality → owning
services add/update/reject offers → provenance recorded by imports services.
Raw retained files use documents metadata. Direct submissions have priority;
scraping is limited to authorized sources and Playwright only when required
(PDF pp. 6, 10). No source URLs in the model are treated as verified integrations.

Validated PostgreSQL data → reusable embedding/projection processing → derived
vector/Neo4j indexes. Jobs must eventually be idempotent; cadence, retry strategy,
freshness, deduplication and deletion propagation remain undecided (Q17–Q18).

## Scaffold limitations

Dagster assets/jobs/resources/schedules/sensors are empty directories. No workflow
states, DAGs, retries, queues or schedules are implemented. LangGraph does not
replace background orchestration, and Dagster does not own interactive dialogue.
