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
not a human advisor assignment or approval step. Reads/drafts need no confirmation;
agent-initiated profile edits, applications, enrollments and external sends require
explicit user confirmation and idempotency keys (Q15).

File metadata/URI → direct text extraction or OCR → NLP/LLM parsing → candidate
review/correction → validated structured profile. Technical processing must not
silently overwrite candidate data. Raw results stay restricted pending candidate
review and remain linked to the CV without an age-based deletion timer.
Generation and ATS evaluation return results to candidate services.

## Imports and synchronization

Admin-approved source and acquisition method → import batch → row
processing/normalization/quality → owning services add/update/reject offers →
provenance recorded by imports services. Automated rows without an external ID are
rejected and recorded; valid rows upsert within `(source, external_id)`. Possible
cross-source duplicates are flagged.
Raw retained files use documents metadata. Direct submissions have priority;
scraping is limited to authorized sources and Playwright only when required
(PDF pp. 6, 10). No source URLs in the model are treated as verified integrations.

Validated PostgreSQL data → reusable embedding/projection processing → derived
indexes where needed. Jobs must be idempotent; imports follow each source's
cadence, retries are bounded, reconciliation is periodic, and rebuilds switch
versions after validation. Exact intervals, retry counts, freshness and deletion
propagation timing remain Q18 contract details.

## Scaffold limitations

Mock interview API requests now persist assistant-owned database jobs in the
request transaction. Session/turn version and idempotency checks are enforced
before answer acceptance; follow-up reservation uses a session row lock. The
application task runner executes graph, TTS/STT and feedback with leases and
committed checkpoints. A separate coordinator publishes durable priority/background
video intents and commits status before acknowledgement. The standalone worker
uses private MinIO audio/results/manifests, a process lock and visibility leases;
it has no Django/database dependency and resolves avatars locally. Local checks
use fake queues and simulated inference; cloud deployment remains unapproved.

Dagster assets/jobs/resources/schedules/sensors are empty directories. No workflow
states, DAGs, retries, queues or schedules are implemented in Dagster. LangGraph does not
replace background orchestration, and Dagster does not own interactive dialogue.
