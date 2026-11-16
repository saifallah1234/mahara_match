# Mock interview local and deployment runbook

The approved [implementation specification](../team/ai_mock_interview_implementation_plan.md)
owns the contract. Local implementation does not authorize deployment. No AWS
resources, instances or queues were inspected or modified during implementation.
One short ElevenLabs test was separately approved. The user subsequently authorized
ElevenLabs for interview speech; local configuration now enables that provider and
paid TTS. This does not itself authorize deployment or additional AWS operations.

## Local application

Use PostgreSQL and private MinIO. The feature migration belongs to Django;
apply it only to the intended development database after inspecting its target.
Seed RBAC with the existing `seed_rbac` command. Commands below assume the repository
root and its configured environment; they are instructions, not proof of deployment.

```bash
uv sync --frozen
uv run --frozen python -m backend.manage migrate
uv run --frozen python -m backend.manage seed_rbac
uv run --frozen python -m backend.manage prepare_interview_avatars
uv run --frozen python -m backend.manage run_interview_tasks
npm --prefix frontend run dev
```

For the local simulated slice use development settings (`DEBUG=True`) or set
`DJANGO_DEBUG=true`, `MOCK_INTERVIEW_ENABLED=true`,
`MOCK_INTERVIEW_BACKEND=mock`, `TTS_PROVIDER=mock`, `STT_PROVIDER=mock` and a working
`INTERVIEW_FFMPEG`. The task runner handles simulated video itself. Simulation
is rejected outside DEBUG; no implicit mock fallback exists.

For real application-side reasoning use `MOCK_INTERVIEW_BACKEND=local` and the
existing `OLLAMA_BASE_URL`/`OLLAMA_MODEL`. Preparation requests an Ollama JSON
schema with exactly three string questions and an introduction; the graph still
validates bounds and uniqueness. Its JSON is validated by the same graph.
A synthetic local preparation check with `qwen2.5:3b` returned three valid French
questions. String-length limits remain in the graph validator because the deployed
server rejected their generated grammar. Full interview reasoning quality remains
unevaluated.

Install optional local speech only when models are available:

```bash
uv sync --frozen --extra local-speech
```

`STT_PROVIDER=faster-whisper` and `TTS_PROVIDER=piper` need this `local-speech` extra.
`run_interview_tasks` builds the configured STT and TTS providers at startup and exits
with an error naming the provider if one cannot be built (missing extra, model or key),
before processing any job. ElevenLabs is only checked for configuration there; no paid
request is made at startup.

Set `TTS_PROVIDER=piper`, `PIPER_MODEL_PATH` to an existing French ONNX voice with
its adjacent `.onnx.json`; set `STT_PROVIDER=faster-whisper`,
`FASTER_WHISPER_MODEL_PATH` to an existing complete model directory (`model.bin`,
`config.json`, `tokenizer.json`; `preprocessor_config.json` is optional, as in the
upstream library). No model is downloaded
during a request. Faster-whisper uses CPU int8 and French VAD transcription.
`INTERVIEW_VOICE` is explicit; Piper records the actual configured model voice.
No local speech model was supplied, so real Piper/STT validation remains blocked.

The ElevenLabs adapter uses `ELEVENLABS_API_KEY`, `TTS_PROVIDER=elevenlabs`,
`INTERVIEW_VOICE=JBFqnCBsd6RMkjVDRZzb`, multilingual v2 and bounded MP3 responses
decoded to measured WAV. Set `INTERVIEW_PAID_TTS_ENABLED=true` only after approving
normal paid use. The one-off test generated “Bonjour, bienvenue à votre entretien
blanc.” (2601 ms, 83298 WAV bytes) in `/tmp/mahara-interview-media/elevenlabs-fr-test.wav`.
That one-off test did not modify `.env` or enable paid interview processing.
The user's subsequent authorization enables `TTS_PROVIDER=elevenlabs`,
`INTERVIEW_PAID_TTS_ENABLED=true` and the explicit voice in local `.env`.
No additional speech API request was made while configuring these values. Do not log API keys.
Provider contract: [ElevenLabs create speech](https://elevenlabs.io/docs/api-reference/text-to-speech/convert).

Avatar sources remain under `video/avatars`. `prepare_interview_avatars` writes
muted 15 FPS forward derivatives under `video/interview-derivatives`, checks
containment and refuses source overwrite. It transfers nothing to EC2. Review
joins visually before release; silent ping-pong effects are deliberately omitted.

## Separate task runner and coordinator

CPU stages use database leases, heartbeats and bounded retries. Run the coordinator
in a separate process so speech/model latency cannot delay publications and status
ingestion. In deployed settings, enable `INTERVIEW_ALLOW_LIVE_AWS=true` only after
cloud approval, and supply the three queue URLs and region.

```bash
uv run --frozen python -m backend.manage coordinate_interviews
```

Both commands support `--once`. Publications remain durable across crashes; a
crash after sending can cause duplicate delivery. Worker generation manifests
reuse completed results, rather than claiming exactly-once GPU execution.
Introduction/Q1 publish at priority; Q2/Q3 wait only for those publications,
then publish to background. Follow-up and closing have no GPU job.

Status acknowledgements follow transaction commit. Unknown/stale/duplicate
events are harmless; invalid output is retained for retry/redrive. Success checks
the expected output prefix, size, SHA256, decodable video/audio and full duration.
Terminal manifests reconcile failed work if status publication fails. A stopped
GPU leaves initial jobs queued; started interviews retain Q2/Q3 fallback audio.

## Worker setup after approval

The supplied instance is g6.2xlarge, Amazon Linux 2023, NVIDIA L4. These are user
facts, not remotely verified facts. Keep the transport worker's Python 3.10 venv
separate from the existing `latentsync` Conda environment. Install only
`infrastructure/latentsync-worker/requirements.txt` there; place this repository's
`pipelines/` and `ai/speech/audio.py` on PYTHONPATH. The worker imports no Django.
Verify all resolved absolute paths using `worker.env.example`.

Before enabling the service, inspect and pin the exact LatentSync Git revision,
UNet/Whisper checkpoints, local cache files, inference CLI flags and actual 15 FPS
pipeline patch. `LATENTSYNC_FPS_VERIFIED=true` is an operator attestation after
inspection, not a patch installer. Ensure inference cannot download missing models
on first use. The adapter uses 8 steps, guidance 1.5 and DeepCache; the reference
[upstream CLI](https://github.com/bytedance/LatentSync/blob/main/scripts/inference.py)
does not establish compatibility with the user's deployed revision.

Source avatars already live on EC2. Set `LATENTSYNC_AVATAR_DIR` to the directory
containing the `avatars/` allowlisted relative filenames. Messages supply keys,
never paths/URLs. Symlinks escaping that root are rejected. The worker downloads
only private TTS, repeats original motion forward to cover full audio at 15 FPS,
invokes Conda with argument lists in isolated scratch space, validates output,
and uploads output/manifests to MinIO. It never downloads or synchronizes avatars.

Create a dedicated unprivileged OS account, root-owned code/runtime configuration
and a mode-0600 `/etc/mahara/interview-worker.env`. Give that account only the
required local avatar/checkpoint read permissions and scratch/state writes.
Copy the service example only after review and approval. Installation/start/stop:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mahara-latentsync
sudo systemctl stop mahara-latentsync
journalctl -u mahara-latentsync --since today
```

No service was installed or started. The process lock under its state directory
enforces one transport/GPU worker per instance. SIGTERM interrupts the service;
systemd kills its subprocesses together. Requests remain unacknowledged and retry
counts survive in MinIO. TemporaryDirectory cleans normal execution; after abrupt
termination, remove only old `latentsync-job-*` directories owned by this service
when it is stopped. Never delete source videos or referenced manifests during recovery.

Rollback: stop worker/coordinator, disable the feature, restore prior code/config.
Preserve migrations, conversations, accepted answers, job rows and manifests.
Do not reverse/drop persistence merely to roll back processing. Inspect queued
generations before resuming.

## Queue, credentials and network policy

User-supplied queues are now configured locally in `eu-central-1`, account
`361769579092`: `mahara-interview-priority`, `mahara-interview-background` and
`mahara-interview-status`. The user reports a fourth queue,
`mahara-interview-priority-dlq`, with By queue redrive permission for the priority
source ARN. These facts have not been checked through live AWS APIs. Background
and status DLQs have not been reported; the target setup below still recommends
one DLQ for each source queue.

The local `.env` and worker environment example contain the three supplied queue
URLs; live AWS remains disabled. The reviewed identity-policy drafts are
[`application-sqs-policy.json`](../../infrastructure/latentsync-worker/application-sqs-policy.json)
and [`worker-sqs-policy.json`](../../infrastructure/latentsync-worker/worker-sqs-policy.json).
Application-policy attachment has not been reported. Deployment operators need
separate DLQ inspection/redrive permissions; the application and worker need no
DLQ access.

The user subsequently reports attaching the EC2 worker IAM role. That attachment
and its effective permissions have not been independently verified; the application
IAM identity is still unspecified. No live AWS API calls or worker deployment
have been performed. Next gate: establish the EC2-reachable private HTTPS MinIO
endpoint, then inspect the existing LatentSync runtime before approved deployment.

Use three standard SQS queues (priority/background/status) with separate DLQs,
encryption and restrictive resource policies. Provision only after approval.
Use an EC2 IAM role, not static AWS keys. Application role: SendMessage only on
request queues, ReceiveMessage/DeleteMessage/ChangeMessageVisibility on status.
Worker role: ReceiveMessage/DeleteMessage/ChangeMessageVisibility on requests,
SendMessage on status. Restrict ARNs and accounts; do not grant EC2 start/stop
or AWS S3 access. Deployment/admin redrive permissions belong to separate operators.

Initial visibility is 900 seconds, extension every 60 seconds, subprocess deadline
3600 seconds, maximum three persisted inference attempts per generation.
Configure transport timing with `INTERVIEW_VISIBILITY_SECONDS`,
`INTERVIEW_HEARTBEAT_SECONDS`, `INTERVIEW_INFERENCE_TIMEOUT_SECONDS` in the worker
environment. Application retry and failed-recording retention use
`INTERVIEW_MAX_ATTEMPTS` (1–3) and positive `INTERVIEW_RECORDING_RETENTION_HOURS`.
Choose a
DLQ maxReceiveCount above inference attempts (for example 8) so upload/status/ack
outages can recover completed work. Calibrate during approved GPU testing. SQS's
12-hour maximum is enforced conservatively at 43100 seconds; loss of visibility
stops inference before output is published. See
[AWS processing guidance](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/best-practices-processing-messages-timely-manner.html).

Inspect invalid messages/DLQs without copying credentials into logs. Terminal
manifests stop new inference. The coordinator reconciles successful/failed manifests
for published jobs; use the owner retry endpoint to create a new generation after
fixing the cause. Do not reset manifest attempt counts or blindly redrive exhausted
generations. Malformed messages require operator review and corrected schema,
not unbounded application retries.

Foreground workers now log startup, received job IDs, generation/inference stages,
completion and failure tracebacks. Failed media subprocesses include only the last
4000 bytes of their diagnostic output; request bodies and audio are not logged.
An idle GPU with a RUNNING job can mean failure before inference: inspect the worker
traceback first. Failed requests remain invisible until their visibility timeout
(900 seconds by default) expires, even after restarting the worker. Do not delete
the lock file or start a second worker to force redelivery.
Local diagnostics checks: all 23 worker unit tests pass, including failure logging,
retained requests and bounded subprocess error output; Ruff and targeted mypy pass.
These checks do not confirm EC2 connectivity or GPU execution.

MinIO is the only asset store. Both identities need GetBucketLocation for SDK
region discovery. Worker credentials need GetObject on
`interviews/tts/*` and GetObject/PutObject on `interviews/worker/*` in the private
bucket. Application credentials need its interview and document prefixes. SQS IAM
does not grant MinIO access. Use private/VPN connectivity and verified HTTPS/CA;
`localhost:9000` cannot reach the application MinIO from EC2. Do not disable TLS
verification, expose an unauthenticated inference endpoint or make media public.
`WorkerStorage` does not create buckets. Provision the bucket independently.

The running local MinIO bucket is `mahara-match`. A live speech-upload failure
revealed invalid configured keys (`SignatureDoesNotMatch`). Separate scoped
application/worker service-account keys were created on that local MinIO and saved
only in ignored, mode-0600 `.env` and `infrastructure/latentsync-worker/worker.env`.
The policies are `application-minio-policy.json` and `worker-minio-policy.json`
under `infrastructure/latentsync-worker/`. Positive read/write and negative scope
checks passed, and temporary probe objects were removed. No paid API was called.
Copy only the updated worker credential values to EC2, preserving its actual
HTTPS endpoint and runtime configuration. EC2 access was unverified at that point.

Subsequent user-supplied EC2 logs confirm request reception, manifest access and
TTS reads, then failure before inference because `/usr/bin/ffmpeg` is absent.
Resolve FFmpeg in the existing LatentSync environment and put that executable's
absolute path in EC2 `INTERVIEW_FFMPEG`; reload configuration and restart the worker.
The runner now rejects a missing FFmpeg at startup before consuming queue jobs.
The updated worker suite passes all 24 tests; Ruff and targeted mypy pass.
After fixing configuration, use the frontend owner retry action for exhausted
required-video jobs; preserve their manifests and successful TTS artifacts.

## Validation and outstanding gates

Phase 1: 8 persistence/API tests. Phase 2: 29 combined contract/graph/API/media,
browser and local MinIO tests. Phase 3: 23 tests, one opt-in MinIO test skipped
in that run; model files unavailable. Phase 4 initial gate: 39 tests, one opt-in
MinIO test skipped; fake queues only. Expanded feature gate: 61 passed, including
real MinIO worker artifacts. Full local regression: 298 passed, one Ollama test
deselected, 23 existing short-test-JWT warnings. Final focused recovery gate:
30 passed; final decoder/media gate: 35 passed. Frontend tests/build and Ruff pass; mypy retains only three baseline
errors in candidate-workspace tests. Exact commands are recorded in the plan.

The opt-in MinIO tests assert localhost and create/delete only unique temporary
buckets. Database settings require a `test_interview_*` name, never the shared DB.
The actual test PostgreSQL was a temporary local cluster on port 55439.

Still required: real Piper/Whisper model validation, French voice comprehension
and quality review, Ollama question/feedback quality evaluation, loop joins,
GPU/LatentSync full-length lip-sync validation, timing/deadline calibration,
verified EC2 runtime/avatar filenames/checkpoints/15 FPS patch, secure remote
MinIO connectivity, queue/IAM/DLQ verification and separate deployment approval.
No deployment or real GPU inference has occurred.
