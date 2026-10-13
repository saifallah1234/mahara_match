# Mock interview API v1

All routes use the existing JWT transport under `/api/v1/mock-interviews/`.
An active candidate needs `assistant.mock_interview.use`; every session, turn,
feedback and media request checks ownership. Recruitment appointments are separate.

| Method/path | Input and behavior |
| --- | --- |
| POST `/` | JSON `offer_id`, optional owned `cv_id`, `language: "fr"`; visible ASCII `Idempotency-Key` (1–255 characters). Returns 202 with durable preparation intent. |
| GET `/` | Owner-only paginated history. |
| GET `/{id}/` | Session status/version, current turn, question/answer text, job stages/statuses, allowed actions, availability and authenticated playback URLs. |
| POST `/{id}/start/` | Rechecks initial media before READY → IN_PROGRESS. Repeated starts return the existing session. |
| POST `/{id}/turns/{turn_id}/answer/` | Multipart `recording`, current integer `version`, `Idempotency-Key`; returns 202. Decodable non-silent audio, at most 180 seconds and 25 MiB. |
| POST `/{id}/retry/` | Retries failed required work with a new generation, preserving accepted answers and the reserved follow-up. |
| POST `/{id}/cancel/` | Cancels progression and unpublished work; schedules raw-recording deletion. Already delivered GPU work may finish, but its result cannot advance a cancelled session. |
| GET `/{id}/feedback/` | Available after COMPLETED: overall `summary` and ordered `questions` containing `turn_id`, `strengths`, `gaps`, actual answer `excerpts`, `improvements`. No hiring score. |
| GET `/{id}/media/{document_id}/` | Owner-scoped private streaming of session playback artifacts. Raw recordings are excluded. |
| GET `/{id}/avatars/{key}/` | Allowlisted avatar; uses a separate muted derivative when available. |

Errors use existing envelopes: 400 invalid/disabled input, 404 inaccessible records,
409 reused keys with changed input or stale/out-of-order transitions, and 503
unavailable required media/provider. Creation does not imply configured providers
or readiness. Background failures leave prepared fallback audio usable.

Exactly three main turns and at most one follow-up are persisted. The follow-up
may follow Q3. Durable transcription precedes raw-recording deletion and routing.
Failed transcription keeps recording bytes for a configurable 24-hour retry
window; expiration restores the same turn for re-recording. Cleanup retries MinIO
outages. Ordinary CV/document routes cannot select interview media and retain
their existing size/type limits.

Browser playback completion never advances server state. Refresh restores the
current persisted question; unsent microphone recordings must be recorded again.
Use shared authenticated blob fetching and release browser object URLs.

READY requires introduction/Q1 generated videos, all three question audios,
closing audio and mandatory avatar templates. Q2/Q3 generated videos are optional.
At a question boundary, unavailable generated video falls back to prepared audio
with a neutral avatar. Playback does not change when a later background result
arrives. Follow-up uses `followup.mp4` muted with separate contextual speech;
the speech clock controls completion and the final video frame holds if needed.

Mock mode requires DEBUG and is visibly simulated. Feature, speech providers,
paid speech and AWS access default to disabled. See the
[local runbook](../deployment/mock_interviews.md) for configuration and release gates.
