# Dated decisions log

Moved verbatim from `CONTEXT.md` (2026-10-21) to keep the always-loaded context small.
`CONTEXT.md` keeps the current architecture. Open items stay in
[open questions](open_questions.md). Add new dated decisions here, newest last.

**User clarification (2026-09-20):** the ANETI employment advisor is the system's
AI agent for recommendations and CV assistance, not a human advisor account.
This supersedes the human-role interpretation in DM §2 and the initial scaffold;
the original source files remain unchanged. See Q22 in the question register.

**Phase 1 gate decisions (2026-09-21):** the user approved the architecture direction
for G01–G10: Django `AbstractUser`, custom RBAC and JWT; UUID keys and timestamps;
role/organization-scoped access and preferred soft deletion for important records;
central taxonomy references and aliases; separate candidate preferences and raw CV
results; offer salary bounds and language fields; retained recruitment history;
import provenance; controlled training/pricing fields; and protected attributable
assistant/audit traces. The exact enum vocabularies, transition matrices, limits and
retention periods not supplied by that decision remain owning-contract details and
must not be invented. See the [Phase 1 gate register](../team/phase_01_data_backend.md#decision-gates-before-coding-the-affected-part)
and [question register](open_questions.md).

**User decisions (2026-09-25):** the PostgreSQL recommendation baseline is a pilot;
the MVP label requires evaluated Phase 7 hybrid plus graph/GraphRAG. Five human
roles remain Candidate, Recruiter, Training Manager, Ministry Manager and Admin.
Offers use TND only with no currency column, superseding the earlier G06 direction.
One candidate preference holds work mode, relocation and maximum commute distance;
one internal Easy Apply application per candidate/offer retains status history.
Frontend technology is React, TypeScript and Vite under `frontend/`. Q01–Q27 in
the [question register](open_questions.md) record the full
decisions and the concrete details still owed by each domain owner.

**Identity onboarding decision (2026-10-08):** candidate registration activates
immediately with a private profile. Recruiter/provider requests remain pending
until an administrator verifies the organization and grants scoped access.
Ministry and admin accounts are provisioned only by privileged administrators.

**Discussion refinements (2026-09-25):** no departments or department labels in
the MVP. Leave existing optional candidate/CV language fields; do not add offer
language requirements or language-based rejection for now. Recruiter access to a
limited profile requires candidate opt-in; submitted CVs go only to the receiving
organization. Training prices are TND, free `0` or paid greater than `0`.
Recruiters may skip optional forward application stages or reject an active
application; candidates may withdraw while active. Hired, rejected and withdrawn
are terminal, with no reapplication to the same offer. Automated import rows
without `external_id` are rejected. Raw CV extraction and conversation history
have no age-based automatic deletion. Account deletion remains soft deletion.
Deleted CV metadata remains for historical references; the CV object-storage bytes
are purged when there are no applications or every linked application is rejected
(2026-10-08 candidate workspace decision). A daily command retries failed purges.
Retained-data policy still needs review before release.

**Frontend wiring audit decisions (2026-10-19):** applying or enrolling discloses the
candidate's name, e-mail and limited profile to that organization only (Q32,
[ADR 0001](../adr/0001-applicant-identity-disclosure.md)). A training program needs at
least one skill to become active. Only admins change organization members; members see
each other read-only. Notifications are in-app only for a fixed event list. Match scores
are recalculated on the candidate's request, not on every publish. The UI stays French-only
for the MVP. Contract and experience values are provisional until Q24. Full list and
tickets: `.scratch/frontend-wiring/spec.md`; terms in [GLOSSARY.md](../../GLOSSARY.md).

**Mock interview implementation (2026-10-11):** the approved
[implementation plan](../team/ai_mock_interview_implementation_plan.md) adds
assistant-owned rehearsal sessions, turns and durable jobs, separate from
recruitment appointments. Phase 1 persistence/API checks pass on isolated local
PostgreSQL. Local phases now include the checkpointed graph, authorized evidence,
protected streaming, recording/cleanup, candidate playback and leased tasks.
Queue coordination and the standalone local-avatar worker pass fake-queue tests;
the complete mocked journey passes Chromium and real local MinIO checks. Optional
Piper/faster-whisper need existing model files, which have not been supplied.
One short ElevenLabs French test was separately approved and decoded successfully;
The user subsequently approved ElevenLabs for interview speech; local configuration
now enables that provider and paid TTS. Cloud access remains separately gated. No deployment or real GPU
inference has occurred. See the [runbook](../deployment/mock_interviews.md) and
[API contract](../api/mock_interviews_v1.md) for configuration and release gates.

**Scoped agent retrieval (2026-10-15):** the ANETI agent serves candidates and
verified recruiters. Candidates get up to 5 visible offers ranked by lexical +
vector + skill-graph retrieval, with matched/missing skills and up to 2 active
training programs per offer as suggestions (not persisted as `OfferMatch`).
Recruiters search `RECRUITERS`/`PUBLIC` limited profiles (Q28; only IDs and matched
skills reach assistant history, details open in discovery, Q29) or their own
offers, drafts included. Routing and replies
cover EN/FR/AR; Tunisian dialect is not covered yet (Q31). An Ollama outage
degrades to lexical + graph and is recorded in the tool trace. Training manager,
ministry and admin retrieval are deferred (Q30). Details: the
[AI architecture](../ai/architecture.md#scoped-retrieval-in-the-agent-2026-10-15)
and the [matching README](../../backend/apps/matching/README.md#production-retrieval-2026-10-15).

**Frontend wiring follow-up (2026-10-21):** the user approved the proposed audit set
(Q33). A recruiter schedules an interview only after the application is at INTERVIEW;
the UI offers a one-click advance from earlier stages and the backend rule stays. An
archived training program can return to draft from the UI ("Remettre en brouillon").
In-app notifications (ticket 25, D12) are written by the owning services in the same
transaction as the change, to the recipients listed in D12 and never to the actor.
Tickets 10 and 26 remain blocked until Q26 and the approved KPIs are settled. Tickets:
`.scratch/frontend-wiring/spec.md`.

**Demo reference vocabulary (2026-11-07):** for the demo seed (`seed_demo`,
`.scratch/demo-readiness/spec.md`), skills come from ESCO v1.2 with their English preferred
labels only (user decision), listed in `backend/apps/taxonomy/data/esco_skills.json`:
canonical name = label, category = ESCO skill type, description = ESCO description plus
`ESCO: <concept URI>`. No schema change, alias table or Arabic/French labels; Q20 stays open.
Education levels are Tunisian diploma names in French, in this order: Baccalauréat, Licence,
Diplôme d'ingénieur, Master, Doctorat. Both are demo vocabulary, not an approved reference.

**Ministry indicators are demo counts (2026-11-07):** `GET /api/v1/reporting/indicators/`
(`.scratch/demo-readiness/issues/04-ministry-indicators.md`) returns all-time counts per
governorate: published, non-deleted offers; applications to them; those applications HIRED;
ACTIVE training programs by provider governorate; empty governorates under "Non précisé".
Skill gaps count counted offers listing a skill against counted programs teaching it
(prerequisites excluded). Reporting owns no tables; recruitment and training expose the
aggregate reads. Access is `reporting.indicators.read` (MINISTRY_MANAGER in a verified
ministry, ADMIN). These are demo counts, not KPIs: Q20's numerator, denominator, time
window, scope and small-count privacy rule remain open.

**Mock interview answer video stays on the device (2026-11-08):** during a mock interview
the candidate's camera is used only for a local preview and a local replay of the answer
(`.scratch/mock-interview-hirevue/issues/02-hirevue-style-interview-stage.md`). The browser
records an audio-only stream for upload and a separate camera-plus-microphone recording held
only in memory; the video is never uploaded or stored and is released after sending,
re-recording or leaving the turn. Only the audio is uploaded and retained under the existing
recording-retention rule (`INTERVIEW_RECORDING_RETENTION_HOURS`). Candidates without a camera,
or who refuse it, answer with audio only. Analysing or sharing answer video needs a separate
privacy decision.
