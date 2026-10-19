# assistant

**Responsibility:** Relational history of assistant interactions and proposed actions.

**Logical entity ownership:** conversations, conversation_messages, agent_executions, agent_tool_calls, agent_actions.

**Sources:** DM §§3.2, 4.E; PDF pp. 7, 9. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Actual agents, prompts, tools and LangGraph execution live in ai/. This domain stores their records through application services; it does not become a second AI runtime.

This includes the ANETI employment advisor, clarified by the user as the system AI
agent for recommendations and CV assistance (2026-09-20; Q22). Its interaction and
execution history belongs here; CV and recommendation records retain their owning domains.

## Current backend

Mock interview rehearsals have separate session/turn/job persistence and
candidate-only `/api/v1/mock-interviews/` routes. Permission seeding adds
`assistant.mock_interview.use`. Creation persists preparation intent, and accepted
answer metadata persists work with version/idempotency checks. Only French is
enabled; feature and integrations default to disabled. The mocked local journey
includes checkpointed graph processing, leased tasks, private media, microphone
recording and deletion retries. Separate queue coordination and standalone worker
code use durable publication/manifests; local tests use fake queues. Optional local
speech requires existing models. One approved ElevenLabs sample passed; ordinary
paid processing remains disabled. No AWS deployment or GPU inference was performed.
See the [API contract](../../../docs/api/mock_interviews_v1.md) and
[runbook](../../../docs/deployment/mock_interviews.md).

The five ORM records and owner-scoped `/api/v1` read routes are initialized.
Users may create, rename and soft-delete their conversations; messages, execution
traces and actions are written only by trusted services. Tool inputs and action
idempotency keys are never returned by public trace serializers. Confirmation,
execution, expiry and replay policy remain the Phase 8 action contract. The initial
schema migration is applied; no agent runtime is included.
