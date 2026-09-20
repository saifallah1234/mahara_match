# assistant

**Future responsibility:** Relational history of assistant interactions and confirmed actions.

**Logical entity ownership:** conversations, conversation_messages, agent_executions, agent_tool_calls, agent_actions.

**Sources:** DM §§3.2, 4.E; PDF pp. 7, 9. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Actual agents, prompts, tools and LangGraph execution live in ai/. This domain stores their records through application services; it does not become a second AI runtime.

This includes the ANETI employment advisor, clarified by the user as the system AI
agent for recommendations and CV assistance (2026-09-20; Q22). Its interaction and
execution history belongs here; CV and recommendation records retain their owning domains.

## Reserved boundaries

- `api/`: future DRF transport, request validation and response representation.
- `services/`: application operations, authorization and business coordination.
- `models/`: future Django ORM definitions owned by this domain.

These directories contain no implementations. No Django app has been initialized.
Cross-domain operations use the owning service; do not duplicate entities or mutate
another domain's models directly. Open requirements are tracked in the
[question register](../../../docs/architecture/open_questions.md).
