# AI mock interview implementation plan

Date: 2026-10-10  
Status: local implementation and documentation complete; cloud deployment and GPU validation unapproved.

This document records the user's agreed plan and subsequent corrections. It is
for the agent implementing the feature in a later task. Creating this document
does not authorize implementation, deployment, live AWS operations or paid
inference in the current task.

## 1. Instructions for the implementing agent

1. Read [AGENT.md](../../AGENT.md), [CONTEXT.md](../../CONTEXT.md),
   [domain boundaries](../architecture/domain_boundaries.md) and this document.
2. Inspect the current repository before editing. The findings below are a
   baseline, not a guarantee that another agent has not changed the code.
3. Implement phases in order. Finish the smallest complete local end-to-end flow
   before advanced infrastructure work. Reuse existing services and patterns.
4. Run the relevant checks after each phase. Fix failures introduced by that
   phase before continuing. Report unrelated baseline failures separately.
5. Update phase status with completed behavior, changed files, exact checks run,
   results, remaining work and blockers. Never describe mocked output as real
   speech recognition or lip-sync.
6. Do not start EC2, deploy a worker, create/change AWS resources, call live AWS
   APIs or send paid inference requests without separate user approval.
7. Do not deploy the EC2 worker until local orchestration and mock integration
   pass. Local success is not production or GPU validation.

Preserve the modular monolith: REST API → application services → Django ORM.
Business state belongs in `backend/`, AI processing in `ai/`, and execution/
orchestration in `pipelines/`. AI code must not import Django models or query the
database directly. Use authorized services through tools or injected callables.

## 2. Agreed MVP and boundaries

- Exactly **three main questions** and **at most one follow-up for the entire
  session**. A follow-up does not count as a main question.
- French first. Design language contracts for `fr`, `en` and `ar-TN`; enable only
  `fr` initially. Reject disabled languages explicitly rather than substituting.
- TTS and STT are provider-configurable. Do not couple the workflow to Piper.
  An ElevenLabs or other adapter must fit the same TTS interface.
- MinIO is the only interview-media object store. No AWS S3 asset dependency.
- LangGraph prepares questions, processes answers, selects the next action and
  generates feedback. Avatar display states are separate frontend concerns.
- Introduction and Q1 generated videos must succeed and be accessible before
  READY. Q2/Q3 videos must not block readiness or question progression.
- Queue Q2/Q3 as early as practical at lower priority than introduction/Q1.
- The dedicated `followup.mp4` is mandatory. Play it with contextual TTS without
  a GPU round trip. **It is not dynamically lip-synced to that TTS.**
- Use prepared closing speech with a suitable existing neutral avatar; no GPU
  dependency for completion.
- Keep source videos unchanged. Derivatives and generated output are separate.
- Scope evidence retrieval to existing authorized records. Do not add full CV
  parsing, vector databases or hybrid/GraphRAG retrieval for this feature.
- Defer autoscaling, multi-GPU coordination, advanced dashboards and
  infrastructure-as-code. Do not defer authorization, validation, durability,
  idempotency, bounded retries or correct message acknowledgement.

This feature's scoped retrieval does not replace the platform's separate hybrid/
GraphRAG release requirement recorded in CONTEXT.md.

## 3. Repository context and reusable components

The repository was inspected across backend domains, AI, pipelines, frontend,
tests, deployment configuration and `video/`. The data model and specification
were also consulted. Some README/context descriptions lag implemented code.

| Area | Existing implementation to reuse |
| --- | --- |
| Backend conventions | Django/DRF, UUID/timestamp base model, migrations, domain errors and pagination |
| Identity/RBAC | JWT, active-user checks, candidate role checks, permission services and RBAC seeding |
| Candidate evidence | `own_profile`, owned records, CV versions, `parsed_data_json`, CV-analysis records |
| Recruitment evidence | Authorized `get_job_offer`, descriptions, offer skills and organization relationships |
| Assistant history | Conversations, messages, executions, tool calls and service-layer persistence |
| AI | `ai/workflows/job_matching.py`: StateGraph, injected tools/functions and conditional routing |
| LLM | `ai/llm/providers/ollama.py`: ChatOllama with environment configuration |
| Storage | `backend/common/storage/object_storage.py`: private MinIO upload/download/delete helpers |
| File metadata | Existing owned `Document` model and trusted metadata-creation service |
| Frontend | React 18/TypeScript/Vite, protected candidate routes, shared UI components, API token refresh and authenticated blob downloads |
| Tests | pytest/pytest-django, storage mocks, grounding tests, Node frontend tests and installed Python Playwright |

Important gaps and constraints:

- Existing recruitment `Interview` records are employer-scheduled appointments
  tied to applications. Do not repurpose or change their lifecycle.
- Add mock-interview persistence to `assistant`; do not activate a new guidance
  app or duplicate candidate, CV, offer or organization models.
- `ai/rag`, vector/graph/hybrid retrieval, document extraction and Dagster paths
  are placeholders, not working integrations.
- No application TTS/STT, SQS integration, LatentSync worker or durable graph
  checkpoint implementation was found.
- `boto3`, Piper and faster-whisper were absent from the project environment.
- The current document API permits PDF/JPEG/PNG and caps downloads at 10 MiB.
  Several avatars exceed that limit. Add media streaming without raising or
  bypassing ordinary document limits.
- Platform-demo narration files under `video/` are not an application speech API.
- Imported offers have `company_name`. Do not automatically describe the import
  owner's organization as the actual employer.
- Local MinIO and Ollama variables are present; connectivity was not tested.
  No AWS, SQS, LatentSync or speech-provider configuration was found locally.

## 4. Avatar inventory and local resolution contract

All seven source files exist under repository `video/avatars/`. Preserve this
exact logical mapping, including spelling:

```python
AVATARS = {
    "base_15": "avatars/avatar_base_15sec.mp4",
    "base_5": "avatars/avatar_base.mp4",
    "thinking_higgs": "avatars/thinking_higs.mp4",
    "thinking_base": "avatars/thinking_avatar.mp4",
    "listening_10": "avatars/listening_higs.mp4",
    "listening_15": "avatars/litsen_nodding_15.mp4",
    "followup": "avatars/followup.mp4",
}
```

| Key | Measured duration | Inspection note |
| --- | ---: | --- |
| `base_15` | 14.41 s | Contains original audio |
| `base_5` | 5.80 s | Contains original audio |
| `thinking_higgs` | 15.04 s | Silent source |
| `thinking_base` | 5.03 s | Silent source; different resolution |
| `listening_10` | 10.04 s | Silent source |
| `listening_15` | 14.04 s | Silent source |
| `followup` | 13.52 s | Contains original audio; 1080×1920 |

Sources have different frame rates/resolutions. Filename durations are not timing
contracts. Mute/remove original audio in playback derivatives so it cannot
compete with generated speech. Visual loop quality still requires review.

### Repository versus EC2

- Repository logical paths resolve relative to `video/` for frontend templates
  and development. Keep that folder; do not synchronize it to EC2 automatically.
- The user confirms all source videos already exist inside `~/LatentSync` on EC2.
  The actual avatar subdirectory and filenames must be verified at deployment.
- Configure `LATENTSYNC_AVATAR_DIR` on the worker. Maintain a local allowlisted
  mapping from the same avatar keys to files within that directory.
- Resolve the chosen file to an absolute path and check directory containment,
  file existence and readability. Reject unknown keys and path escapes.
- If deployed filenames differ, use trusted deployment configuration to map the
  logical keys. Never accept a path or filename override from an SQS message.
- Missing local avatars fail the job. Do not download or copy source video from
  Django, MinIO or another server as a fallback.

## 5. Persisted state and authorization

Use three new assistant-owned models with the existing UUID/timestamp base:

| Model | Responsibilities |
| --- | --- |
| `MockInterviewSession` | Candidate, offer, optional owned CV, conversation, language, status, current turn, version, source-referenced evidence snapshot, workflow checkpoint, feedback and error |
| `MockInterviewTurn` | Main/follow-up kind, main position or parent turn, question/answer message references, recording, transcription state, evaluation and media references |
| `MockInterviewJob` | Task/stage, generation, input fingerprint, publication state, execution status, attempts, lease/heartbeat, source avatar, media references, configuration fingerprint and sanitized error |

Reuse `ConversationMessage` for canonical question/answer text, execution/tool
records for AI traces and `Document` for stored-file metadata. Keep final
structured feedback on the session.

Required invariants:

- Main positions are 1–3 and unique per session; preparation must create exactly
  three before readiness. At most one follow-up row per session, enforced with a
  conditional unique constraint.
- Reserve the follow-up under a session lock before generation. A failed
  generation retries that same turn rather than consuming another opportunity.
- One accepted answer per turn. Duplicate requests return the original result;
  reusing an idempotency key for different input fails.
- Validate current turn and session version. Reject stale/out-of-order requests.
- Use short transactions; execute model/storage/queue work outside locks and
  commit results with generation/version checks.
- Never advance solely because the browser reports playback completion. Answer
  acceptance and server-side routing determine the next interview turn.

Session lifecycle:

```text
PREPARING → READY → IN_PROGRESS ↔ THINKING → EVALUATING → COMPLETED
                      ↘ explicit FAILED / CANCELLED paths
```

Job lifecycle:

```text
PENDING → QUEUED → RUNNING → SUCCEEDED
                   ↘ RETRY_WAIT / FAILED / CANCELLED as appropriate
```

Recoverable recording/STT errors leave the current turn available for retry.
Worker availability is separate from successful completion.

### Access and retention

- Seed `assistant.mock_interview.use` for candidates through existing RBAC.
- Require an active candidate plus session ownership for all session, answer,
  feedback and media operations. Other candidates/recruiters gain no access.
- Read candidate/CV/offer evidence through owning services. Do not expose raw
  storage keys, credentials or internal error traces in public responses.
- Keep interview media out of ordinary CV selection and reject it as a CV source.
- Treat source text and answers as untrusted model inputs. Model output cannot
  choose arbitrary records, object paths, network endpoints or shell arguments.
- Purge raw recordings after durable transcription. Failed-STT recordings have
  a configurable 24-hour retry window, then require re-recording. Persist pending
  deletions so a MinIO outage does not silently prevent cleanup.
- Preserve existing CV-deletion behavior. Interview references do not retain
  deleted CV bytes or change the current application-linked retention rules.

## 6. Public API contract

All paths below are relative to `/api/v1/mock-interviews/`.

| Method/path | Contract |
| --- | --- |
| `POST /` | `{offer_id, cv_id?, language:"fr"}` plus `Idempotency-Key`; return `202` and session/preparation state |
| `GET /` | Owner-only paginated history |
| `GET /{id}/` | Version, current turn, allowed actions, actual preparation/job statuses, availability, errors and playback descriptors |
| `POST /{id}/start/` | Idempotent READY transition; recheck required media access |
| `POST /{id}/turns/{turn_id}/answer/` | Multipart recording, expected session version and idempotency key; return `202` |
| `POST /{id}/retry/` | Retry eligible failed work without duplicating answers or follow-up turns |
| `POST /{id}/cancel/` | Stop progression and suppress unpublished work |
| `GET /{id}/feedback/` | Completed structured feedback |
| `GET /{id}/media/{document_id}/` | Authenticated owner-scoped streaming |
| `GET /{id}/avatars/{key}/` | Allowlisted frontend template playback |

Use existing error envelopes: `400` invalid input/disabled language, `404`
inaccessible records, `409` state/version conflict, `503` required integration
unconfigured/unavailable. Required configurations must not silently fall back to
successful mock results.

Use API media paths and existing authenticated blob fetching. Release browser
object URLs after use; prefetch small TTS files and at most the next video.

## 7. LangGraph, speech and frontend behavior

### Evidence and graph processing

An authorized evidence service returns bounded serializable profile/history/
skill data, selected CV parsing results if present, selected-offer requirements
and relevant stored company information. Retain source identifiers and explicit
missing-evidence notices. Select relevant evidence deterministically; no new
embedding or scraping pipeline is required.

Processing graph:

```text
prepare_interview → generate_questions → prepare_media → persist and exit

accepted recording → process_answer → decide_next
                                      ├─ generate_followup → prepare_media
                                      ├─ activate next main question
                                      └─ evaluate_interview → feedback + closing
```

Use conditional edges for routing. A follow-up after Q3 is permitted; evaluate
only when all three mains and any pending follow-up have accepted answers.
Follow-up answers never create another follow-up.

Persist application-level checkpoints with graph version, completed step,
serializable state, turn and input fingerprint through backend services. Resume
from committed state and skip completed work. Do not keep a graph execution
alive while waiting for a person; do not add a second database/checkpoint system.

Validate structured question/evaluation output. Feedback includes per-question
strengths, gaps, supporting answer excerpts, improvements and an overall summary.
Do not invent a numerical hiring score or make an employment decision.

### Speech providers

```text
synthesize(text, language, voice) → audio artifact + duration
transcribe(audio, language) → transcript + metadata
```

Select adapters with `TTS_PROVIDER` and `STT_PROVIDER`; provider-specific
configuration stays inside adapters. Persist provider/model/voice information
with generated artifacts. Start with deterministic mocks. Add optional local
Piper TTS and faster-whisper STT adapters without making either mandatory.

An ElevenLabs or other adapter must use the same TTS contract. Do not implement
every possible provider up front or enable paid calls without approval. Optional
speech dependencies/model files must be explicit, not downloaded during requests.

Run speech on the application-side task worker so a stopped GPU instance does
not disable STT or fallback TTS.

### Scheduling and readiness

| Stage | Source and playback | Scheduling |
| --- | --- | --- |
| Introduction | Generated video from `base_15` | High priority; required |
| Q1 | Generated video from `base_5` | High priority; required |
| Q2 | Generated video from `listening_15`, otherwise TTS + neutral avatar | Early background |
| Q3 | Generated video from `listening_10`, otherwise TTS + neutral avatar | Early background |
| Follow-up | Dedicated `followup.mp4` + contextual TTS | No GPU job |
| Closing | Prepared French closing TTS + suitable neutral avatar | No GPU job |

Generate and publish introduction/Q1 first. Publish Q2/Q3 as soon as their TTS
exists and initial priority requests have been published. Do not wait for initial
inference success before queuing background work. Check priority work before
starting background inference; do not preempt running inference.

READY requires three valid questions, accessible successful introduction/Q1
videos, prepared main-question fallback audio and available required templates.
Q2/Q3 generated videos never gate READY. Prepare their audio and fixed closing
speech while initial GPU work runs.

At each question boundary use a buffered generated video, otherwise prepared TTS
with a neutral avatar. Do not switch midway through spoken text. An optional
video failure must not fail an otherwise usable interview.

### Frontend and recording

```text
PREPARING → READY → INTRO → SPEAKING → LISTENING → UPLOADING → THINKING
                                                               ↓
                                  follow-up / next main / evaluation + closing
```

- Show actual job/stage states, not simulated progress percentages.
- Show thinking animation during STT, evaluation and follow-up generation.
- Record only in LISTENING with explicit start/stop controls. Initially limit
  answers to three minutes/25 MiB, validated by decoding on the server.
- Handle permission denial, unsupported recording formats, silence, upload
  interruption, expired login and retries without duplicate answers.
- Restore the persisted current turn on refresh. Unsubmitted interrupted audio
  must be recorded again.
- Include question text, keyboard controls, microphone indicators and reduced
  motion support using existing UI components.
- Follow-up playback mutes original audio and uses contextual TTS as the clock.
  Hold its last frame if speech outlasts the clip. Label the non-lip-sync limitation.
- Use separate muted derivatives for smooth silent loops. Default to forward
  looping with reviewed joins; pre-render ping-pong only for suitable silent
  footage. Never reverse visible generated speech.

### Full-length lip-sync

Measure TTS duration. Prepare a temporary local source timeline long enough for
the full audio, normalize to the verified processing FPS and run LatentSync over
the entire timeline. Use forward source repetition with reviewed joins when
extension is needed. Never repeat an already lip-synced output or truncate speech.
Validate output decoding, audio presence and duration against the input audio.

## 8. Queue and EC2 worker contract

```text
Django → SQS request (job + avatar key + audio reference)
       → EC2 worker (existing local avatar + MinIO audio)
       → local LatentSync → MinIO generated MP4
       → SQS status event → Django durable job status
```

SQS transports jobs; it does not run LatentSync. Django never calls a public EC2
inference endpoint. The EC2 worker needs no Django database credentials.

### Request schema

```json
{
  "schema_version": 1,
  "job_id": "<uuid>",
  "generation": 1,
  "input_fingerprint": "<sha256>",
  "avatar_key": "base_15",
  "audio": {
    "object_key": "<private MinIO interview-input key>",
    "sha256": "<sha256>",
    "duration_ms": 18000
  }
}
```

Derive output prefixes from validated job ID/generation. Approved inference
configuration belongs to the worker, not arbitrary message arguments. Reject
video paths/URLs, unknown avatar keys, unexpected audio prefixes, invalid IDs,
fingerprints and unsupported schema versions. Send no candidate profile, CV,
transcript or credentials to the GPU worker.

Status events carry event ID, job/generation/fingerprint, execution identifier,
attempt, state/heartbeat and validated output metadata. Ignore duplicate/stale
events. A late RUNNING event cannot overwrite SUCCEEDED. Verify output references
and availability before persisting successful completion.

### Application-side orchestration

- Use database-backed jobs for graph, TTS/STT and feedback tasks.
- Persist publication intent in `MockInterviewJob` before sending SQS messages;
  replay unpublished work after crashes. `transaction.on_commit()` alone is not
  sufficient durability.
- Provide a task runner and coordinator management command; keep long speech/
  model work from blocking publication, result ingestion and cleanup.
- Use database leases and bounded retries for CPU tasks. Prioritize accepted
  answers/follow-up speech over speculative media.
- Use priority requests, background requests and worker-status queues, with
  dead-letter handling. Acknowledge status events only after database commit.

### Worker processing and acknowledgement

1. Validate request and inspect its durable attempt/result manifest in MinIO.
2. Reuse a previously validated completed result on redelivery.
3. Resolve the allowlisted avatar locally and persist the next attempt.
4. Download **only TTS audio** from MinIO; verify integrity.
5. Prepare temporary local input files and invoke configured LatentSync using
   an argument list, configured working directory and isolated job scratch space.
6. Validate the MP4, upload output and durable result manifest to MinIO.
7. Publish success to the SQS status queue.
8. Delete the request only after durable output and accepted status publication.

Before live SQS use, enforce one GPU worker on this EC2 instance with a process
lock and durable attempt manifests. Default to three inference attempts per job
generation. Duplicate delivery must not reset retry counts. A failed status send
must reuse completed output on redelivery rather than regenerate immediately.

Failures stay unacknowledged for retry/redrive; terminal failure manifests stop
new inference while messages move to the DLQ. Reconcile terminal failures into
Django. Idempotency protects business results; do not claim exactly-once GPU
execution across every crash boundary.

Use long polling and visibility extension. Initial configurable defaults are
15-minute visibility, 60-second heartbeats/extensions and a 60-minute subprocess
deadline; calibrate during approved GPU validation and respect SQS's 12-hour
visibility limit. Stop/retry safely when continued processing loses its lease.

A stopped/unavailable GPU leaves initial work queued/stalled, not complete. An
already-started interview can use Q2/Q3 fallback audio. No auto-start of EC2.

### MinIO and mock mode

Extend the existing adapter with streaming, metadata checks and bounded reads.
Use private prefixes for TTS, temporary recordings, outputs and worker manifests.
Do not introduce S3 or avatar-transfer infrastructure.

Use a fake queue/provider implementation and mock media runner locally. Exercise
the same envelopes, state transitions and storage contracts. Mark outputs as
simulated; production configuration must reject mock providers/results.

## 9. Phase-by-phase implementation checklist

All file paths are repository-relative. Recheck migration numbering and existing
files before creating them; add package `__init__.py` files only where required.

### Phase 1 — Persistence, RBAC and API

**Context:** No mock-interview domain implementation exists. Establish a secure,
testable state machine without requiring any speech, GPU or queue service.

Create:

- `backend/apps/assistant/models/mock_interviews.py`
- `backend/apps/assistant/migrations/0002_mock_interviews.py`
- `backend/apps/assistant/services/mock_interviews.py`
- `backend/apps/assistant/services/interview_contracts.py`
- `backend/apps/assistant/services/bootstrap.py`
- `backend/apps/assistant/api/mock_interview_serializers.py`
- `backend/apps/assistant/api/mock_interview_views.py`
- `tests/unit/backend/test_mock_interview_contracts.py`
- `tests/integration/assistant/test_mock_interviews.py`

Modify:

- `backend/apps/assistant/models/__init__.py`
- `backend/apps/assistant/api/urls.py`
- `backend/apps/identity/management/commands/seed_rbac.py`
- `backend/config/settings/base.py` and `.env.example`

Tasks:

- [x] Add models, constraints, migration, status transitions and owner checks.
- [x] Add candidate permission seeding and public API validation/idempotency.
- [x] Add language contracts and disabled-by-default integration settings.
- [x] Persist requested work without performing external operations in API calls.
- [x] Update ownership/context documentation to describe implemented additions.

Tests: isolated migration, cross-candidate/role access, invalid offer/CV,
three-main-position constraints, single follow-up, stale versions, duplicate
answers/requests, invalid transitions and retry identity.

**Exit gate:** persistence and API tests pass without cloud/GPU/provider calls.
This phase alone is not a working spoken interview.

### Phase 2 — Complete local flow with mocked providers

**Context:** Build a vertical slice using Phase 1 services. Use local MinIO and
deterministic model/speech/video doubles for repeatable integration tests.

Create:

- `backend/apps/assistant/services/interview_evidence.py`
- `backend/apps/assistant/services/interview_jobs.py`
- `backend/apps/assistant/services/interview_media.py`
- `backend/apps/assistant/management/commands/run_interview_tasks.py`
- `ai/workflows/mock_interview.py`
- `ai/tools/interview_evidence.py`
- `ai/llm/prompts/mock_interview.py`
- `ai/speech/providers.py`
- `pipelines/interviews/mock.py`
- `frontend/src/api/mockInterviews.ts`
- `frontend/src/lib/mockInterviewMachine.ts`
- `frontend/src/components/interview/AvatarPlayer.tsx`
- `frontend/src/components/interview/AnswerRecorder.tsx`
- `frontend/src/pages/candidat/MockInterview.tsx`
- `tests/unit/ai/test_mock_interview.py`
- `tests/integration/assistant/test_interview_jobs.py`
- `tests/integration/assistant/test_interview_media.py`
- `tests/e2e/test_mock_interview.py`
- `frontend/tests/mockInterviews.test.mjs`

Modify the candidate/recruitment services for authorized evidence projections,
and `frontend/src/App.tsx`, `frontend/src/pages/candidat/OffreDetail.tsx` and
`frontend/src/components/layout.tsx` for routes and entry points. Add the minimal
MinIO streaming support needed by this slice now; do not defer necessary storage
work simply because real media validation continues in Phase 3.

Tasks:

- [x] Implement checkpointed graph, evidence retrieval and structured feedback.
- [x] Implement fake queue, mock providers and mock generation with explicit labels.
- [x] Implement preparation, actual job-status polling, playback and recording UI.
- [x] Implement introduction/Q1 gating, early background jobs and Q2/Q3 fallback.
- [x] Implement follow-up reservation, dedicated playback and resume/retry.
- [x] Implement recording cleanup and protected media access.

Tests: complete three-question interview, no follow-up, follow-up after each main,
no second follow-up, malformed LLM output, missing evidence, STT failure/silence,
checkpoint restart, duplicate submission, feedback failure/retry, recording purge,
readiness and nonblocking fallback. Include a browser journey and verify no AWS
or paid calls are made.

**Exit gate:** complete interview from preparation through report works locally
with mocks. Do not deploy EC2 before this gate passes.

### Phase 3 — Real local speech and media validation

**Context:** Replace only configured adapters; preserve the tested orchestration.
Keep paid providers disabled. Local speech is independent of the EC2 GPU.

Add:

- `ai/speech/piper.py` and `ai/speech/faster_whisper.py` as optional adapters.
- `backend/apps/assistant/management/commands/prepare_interview_avatars.py` for
  local derivative preparation; it must never synchronize originals to EC2.
- Speech and avatar/media validation cases in the relevant tests.

Modify `ai/speech/providers.py`, storage/media services,
`backend/apps/documents/services/documents.py`, settings/env examples and
`pyproject.toml`/`uv.lock`. Extend existing document/CV tests to protect behavior.

Tasks:

- [x] Select local providers through configuration, not graph branching by vendor.
- [x] Require explicit local models/voice; no request-time model downloads.
- [x] Validate input audio format/duration/size and record provider metadata.
- [x] Prepare separate muted smooth-loop derivatives; preserve originals.
- [x] Verify full follow-up audio and closing playback without GPU dependency.

Tests: provider selection, absent configuration, disabled languages, malformed
audio, limits, speech failure, original-audio muting, long follow-up speech,
media authorization and source preservation. Verify ordinary document/CV APIs
retain their limits and behavior.

**Exit gate:** configured French local speech works, or any unavailable model/
voice is reported as a blocker while mock tests remain green. Do not label a
mock-only result as a working real speech integration.

### Phase 4 — SQS and local-avatar GPU worker implementation

**Context:** Implement the deployment contract without deploying or calling live
AWS. Use fake AWS clients and local test files for worker integration checks.

Create:

- `pipelines/interviews/queue.py`
- `pipelines/interviews/worker.py`
- `pipelines/interviews/latentsync.py`
- `backend/apps/assistant/management/commands/coordinate_interviews.py`
- `tests/unit/pipelines/test_interview_worker.py`
- `infrastructure/latentsync-worker/requirements.txt`

Extend job integration tests and update settings/env examples,
`backend/common/storage/object_storage.py`, `pyproject.toml` and `uv.lock`.
Add `boto3` only when needed here. Keep the lightweight worker's dependencies
separate from the existing LatentSync Conda environment; ensure worker code can
run under its documented Python version.

Tasks:

- [x] Implement durable publication, priority/background routing and status ingestion.
- [x] Implement allowlisted local-avatar resolution; messages carry keys only.
- [x] Download only audio; upload output/results to MinIO.
- [x] Invoke the configured Conda runtime safely with isolated scratch files.
- [x] Implement retry manifests, single-worker lock, heartbeats/visibility extension,
  output validation, deduplication and correct acknowledgement.
- [x] Implement unavailable-worker and terminal-failure reconciliation.

Tests: unknown key/path injection/symlink escape, missing local avatar, no source
video transfer, audio checksum mismatch, priority ordering, duplicate publication/
delivery, stale events, crash before/after upload/status/ack, retry exhaustion,
DLQ handling, visibility loss, subprocess timeout and stopped GPU behavior.

**Exit gate:** worker orchestration and mock integration pass without AWS. Real
LatentSync timing and quality remain unverified until approved GPU validation.

### Phase 5 — Runbook and separately approved deployment validation

**Context:** Documentation and configuration examples are local work. Deployment,
AWS operations and real cloud inference require explicit approval.

Create:

- `infrastructure/latentsync-worker/mahara-latentsync.service`
- `infrastructure/latentsync-worker/worker.env.example`
- `docs/deployment/mock_interviews.md`
- `docs/api/mock_interviews_v1.md`

Tasks:

- [x] Document worker dependencies, runtime setup, restricted environment files,
  systemd installation/start/stop, logs, scratch cleanup and rollback.
- [x] Document IAM roles/queue policies, DLQ recovery, retry defaults and MinIO
  TLS/private connectivity with least-privilege credentials.
- [x] Record local test results and exact remaining production checks.
- [ ] After approval only: inspect deployed revision, local patches, filenames,
  absolute paths, checkpoints, CLI flags and GPU availability.
- [ ] After approval only: validate each assigned avatar, full-length speech,
  interrupted inference, 15 FPS timing and measured processing deadlines.

**Exit gate:** distinguish documentation complete, deployment approved and real
GPU validation passed. Never combine them into a single assumed completion.

## 10. EC2 facts, configuration and release blockers

The user supplied these existing EC2 facts; they were not remotely verified:

| Setting | Supplied value |
| --- | --- |
| Instance/OS/GPU | `g6.2xlarge`, Amazon Linux 2023, NVIDIA L4 |
| LatentSync checkout | `~/LatentSync` |
| Conda environment | `latentsync`, Python 3.10 |
| UNet checkpoint | `~/LatentSync/checkpoints/latentsync_unet.pt` |
| Configuration | `configs/unet/stage2_512.yaml` |
| Whisper checkpoint | `checkpoints/whisper/tiny.pt` |
| Inference | 8 steps, guidance scale 1.5, DeepCache enabled |
| Processing FPS | Pipeline modified from 25 to 15 |
| Source avatars | Already present inside the LatentSync repository; exact directory to verify |

Resolve `~` and relative paths explicitly in trusted deployment configuration.
Do not assume that setting an FPS environment variable changes the deployed
pipeline. Verify the actual code patch and invocation before claiming support.

Required configuration groups:

- Feature enablement, local/mock/live backend selection and enabled languages.
- Provider names plus provider-specific model/voice/path settings.
- Explicit disabled-by-default gates for live AWS and paid provider calls.
- AWS region, priority/background/status queue URLs and dead-letter configuration.
- Existing MinIO settings plus EC2-reachable endpoint, verified TLS/CA and scoped
  credentials. `localhost:9000` is not an EC2 connectivity solution.
- Conda executable/environment, LatentSync checkout/config/checkpoint paths,
  expected revision, inference parameters and `LATENTSYNC_AVATAR_DIR`.
- Recording limits, failed-STT retention, retry limits, heartbeat/visibility and
  inference timeout settings.

Use an EC2 IAM role for SQS instead of static AWS keys where possible. The worker
needs restricted MinIO credentials for required audio/output/manifest prefixes;
SQS IAM credentials do not automatically grant MinIO access. No public
unauthenticated inference endpoint is permitted.

Remaining release gates: French voice/model selection and quality, secure
EC2-to-MinIO connectivity, actual deployed runtime/avatar path verification,
loop/lip-sync visual quality and separate approval for cloud work. These do not
justify blocking Phase 1 or the mocked local vertical slice.

## 11. Verification and progress reporting

Repository-prescribed checks when implementation starts:

```bash
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy .
# Run the relevant pytest paths for the current phase.
uv run --frozen pytest <phase-test-paths>
npm --prefix frontend test
npm --prefix frontend run build
```

Run frontend checks when frontend code changes; expand regression coverage when
shared adapters/contracts change. Test migrations and transactional behavior on
an explicitly isolated PostgreSQL database. Test settings inherit base settings:
do not assume the default configuration is an isolated test database. Do not run
integration checks against the configured shared database.

During implementation, update `CONTEXT.md`,
`docs/architecture/domain_boundaries.md`,
`docs/architecture/open_questions.md`,
`docs/workflows/orchestration.md` and `backend/apps/assistant/README.md` as the
relevant decisions become implemented. Do not rewrite original business sources.

| Phase | Current status | Evidence |
| --- | --- | --- |
| 1 — Persistence/API | Complete locally | 8 contract/API tests passed on isolated PostgreSQL 16; migration applied by pytest on a fresh test database. Ruff clean after fixing import order; format passes. mypy has 3 pre-existing errors in tests/integration/test_candidate_workspace.py; no new errors. Media/provider endpoints explicitly unavailable pending Phase 2. |
| 2 — Local mocked flow | Complete locally | 29 tests passed together, including Chromium journey and real local MinIO temporary-bucket flow. Speech, reasoning and generated-video behavior are explicitly simulated. Frontend test/build passed. No AWS or paid calls. |
| 3 — Local speech/media | Complete locally; local-model validation blocked | 23 tests passed, one opt-in MinIO test skipped in this phase run (passed in Phase 2). Optional Piper/faster-whisper adapters require explicit existing models; none supplied. Muted derivative/source preservation and decode/limit/silence checks pass. User separately approved one ElevenLabs French test on 2026-10-11: decoded 2601 ms WAV, 83298 bytes; normal paid usage remains disabled. |
| 4 — Queue/worker | Complete locally; GPU validation pending | Initial gate: 39 passed, one opt-in MinIO test skipped. Expanded feature gate: 61 passed, including real local MinIO worker/result flow. Fake queues exercise priorities, publication crashes, stale generations, result reuse, status/ack failures, retries, process lock, path/checksum validation, visibility loss, subprocess deadlines, output duration and stopped-worker state. No AWS calls. Real LatentSync runtime/quality unverified. |
| 5 — Runbook/validation | Documentation complete; deployment pending approval | Added API/runbook, protected worker environment example and systemd unit. Full local regression: 298 passed, one Ollama test deselected; 23 existing test-JWT warnings. Final focused recovery checks: 30 passed. Frontend: four test files and build pass. Browser checks cover follow-up final-frame holding, audio-clock completion and closing. Ruff clean; mypy retains only three pre-existing candidate-workspace test errors. Cloud/IAM/remote MinIO/GPU/voice quality gates remain open. |

### Local validation commands and artifacts (2026-10-11)

New implementation files are listed in each phase above, plus the small Ollama
interview adapter (`ai/llm/providers/interview.py`), audio decoding helper,
standalone worker MinIO adapter/entry point and assistant queue coordinator service.
`boto3` is the queue transport dependency; local speech remains an optional extra
in `pyproject.toml`/`uv.lock`. Model files are never installed during requests.

Full regression command (isolated temporary PostgreSQL, local MinIO only):

```bash
UV_CACHE_DIR=/tmp/mahara-uv-cache \
MINIO_ACCESS_KEY=minioadmin MINIO_SECRET_KEY=minioadmin \
PLAYWRIGHT_BROWSERS_PATH=/tmp/mahara-playwright \
INTERVIEW_TEST_DB_NAME=test_interview_final_regression INTERVIEW_TEST_MINIO=1 \
INTERVIEW_FFMPEG=/tmp/mahara-interview-media/ffmpeg \
uv run --frozen pytest --ds=backend.config.settings.interview_test -m 'not ollama' -q
```

Result: 298 passed, one Ollama test deselected, 23 existing short-test-JWT warnings.
The MinIO credentials above are the repository's public development Compose
defaults, not `.env` secrets. Tests create/delete only temporary buckets.

Final recovery gate: same isolated settings and FFmpeg, database
`test_interview_recovery_final`, pytest paths
`tests/integration/assistant/test_interview_jobs.py` and
`tests/unit/pipelines/test_interview_worker.py`: **30 passed**.
TTS reuses persisted audio/provider metadata after an upload/commit crash.
Incomplete upload cannot silently cause new provider calls in that generation;
operator retry creates a new generation after storage recovery.

Final decoder/media gate (database `test_interview_decoder_final`), pytest paths
`tests/integration/assistant/test_interview_media.py`,
`tests/unit/pipelines/test_interview_worker.py` and
`tests/integration/assistant/test_interview_jobs.py`: **35 passed**. Decoders
allow only supported media containers and local input protocols, rejecting
uploaded playlists that reference other URLs.

Ruff check/format pass; `uv run --frozen mypy .` reports only the baseline three
errors in `tests/integration/test_candidate_workspace.py` (lines 63, 73, 114).
`npm --prefix frontend test` passes four files; `npm --prefix frontend run build`
passes. `makemigrations --check --dry-run` detects no missing migrations; its
history check warned that the disposable schema-check database did not exist.
Fresh migration application is covered by isolated PostgreSQL pytest runs.

All seven local muted derivatives were prepared without modifying sources.
Visual join/speech quality remains a human/GPU validation gate. The approved
ElevenLabs sample is `/tmp/mahara-interview-media/elevenlabs-fr-test.wav` (2601 ms,
83298 bytes). No other paid inference or live AWS operations occurred.

After each phase report completed behavior/files, actual check results, remaining
work and blockers. Record mocked versus live validation explicitly. Do not mark
an unavailable integration complete or let a mock fallback hide a failure.

## 12. Reference checks for later runtime verification

- [LatentSync inference CLI](https://github.com/bytedance/LatentSync/blob/main/scripts/inference.py)
- [LatentSync pipeline](https://github.com/bytedance/LatentSync/blob/main/latentsync/pipelines/lipsync_pipeline.py)
- [SQS visibility and processing duration](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/best-practices-processing-messages-timely-manner.html)
- [Piper local TTS](https://github.com/OHF-Voice/piper1-gpl)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)

Upstream behavior is reference material, not proof of the deployed EC2 revision.
Original avatar files, live infrastructure and runtime environments were not
modified while preparing this handoff.
