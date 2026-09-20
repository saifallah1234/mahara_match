# guidance (reserved)

Future scope: AI-assisted candidate guidance, including recommendations and CV assistance.

**User clarification (2026-09-20, Q22):** the ANETI employment advisor is the system's
AI agent, not a human advisor. This supersedes the assignment interpretation of
PDF p. 3 and DM §§2, 7 (physical PDF pages include the cover).

This README is a scope marker only, not a commitment to a separate Django app.
Reasoning and workflows belong in ai/; assistant owns interaction history;
candidates owns CVs and analysis; matching and training own their recommendation
records. Use tools and owning application services for relational access.

There are no human advisor accounts or assignment workflows implied here. No
schema, initialized Django app or API/services/models skeleton exists. Clarify
delivery scope and whether any additional business state is needed in the
[open question register](../../../docs/architecture/open_questions.md) before
implementation; reuse existing domain concepts and preserve candidate validation.
