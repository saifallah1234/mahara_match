# Domain boundaries and entity ownership

Sources: [DM](../../mahara_match_data_modeling.md) and
[PDF](../../Cahier%20de%20charge%20pr%C3%A9liminaire%20PDF.pdf).
DM references use source section numbers; PDF references are physical pages including the cover.
Logical identifiers below preserve source spelling; they are not generated Django model names.

User clarification (2026-09-20, Q22) supersedes the human ANETI advisor interpretation
in DM §2: the advisor is the system AI agent for recommendations and CV assistance.
The identity entities below do not imply an `ANETI_AGENT` human account role.

## Canonical ownership

| Domain | Logical entities owned | Source |
| --- | --- | --- |
| `identity` | `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `organizations`, `organization_members` | DM §4.A; PDF pp. 3–4, 6 |
| `candidates` | `candidate_profiles`, `experiences`, `educations`, `candidate_languages`, `candidate_skills`, `Certifications`, `candidate_preferences`, `projects`, `cvs`, `cv_analysis_results` | DM §4.B; PDF pp. 5–6, 9 |
| `documents` | `documents` | DM §§4.B, 4.F, 5; PDF p. 9 |
| `taxonomy` | `skills`, `skill_aliases`, `languages`, `education_levels` | DM §§3.1, 4.B; PDF pp. 4, 9 |
| `recruitment` | `job_offers`, `offer_skills`, `applications`, `application_status_history`, `interviews` | DM §4.C; PDF pp. 3, 5–6, 10 |
| `matching` | `offer_matches`; derived `embeddings` index | DM §4.C; PDF pp. 5, 9 |
| `training` | `training_programs`, `training_skills`, `training_sessions`, `training_enrollments`, `training_recommendations` | DM §4.D; PDF pp. 3, 5–6 |
| `assistant` | `conversations`, `conversation_messages`, `agent_executions`, `agent_tool_calls`, `agent_actions` | DM §§3.2, 4.E; PDF pp. 7, 9 |
| `imports` | `data_sources`, `import_batches`, `import_rows` | DM §§3.3, 4.F; PDF pp. 6, 10 |
| `platform` | `notifications`, `audit_logs` | DM §4.E; PDF pp. 4, 6–7 |

`skill_aliases` appears in the relationship diagram without a full table dictionary.
`Certifications` retains the source's capitalization here only; implementation naming is deferred.
`education_levels`, preferences and projects appear in the dictionary despite incomplete diagram coverage.

## Reserved domains

| Domain | Documented scope | Missing detail |
| --- | --- | --- |
| guidance | AI-assisted candidate guidance scope marker; advisor execution belongs in ai/ (user clarification, Q22; supersedes assignment interpretation of PDF p. 3 and DM §§2, 7) | Delivery scope and whether any distinct business state is needed beyond existing domains; no human advisor assignments |
| reporting | Ministry aggregate indicators (PDF p. 4; DM §2) | Metric definitions, aggregation/privacy and MVP timing |
| community | Forum, reports and moderation (PDF pp. 5, 7, 10) | Schema, moderation workflow and delivery timing |

These areas contain README files only. They do not imply approved models or MVP inclusion.

## Interface organization

Implemented domains use `api/`, `services/` and `models/`. APIs adapt transport
to application-service operations; services own business validation and
authorization; models implement domain-owned ORM state. Imports, assistant and
platform records remain pending, and no application migrations have been created.

Cross-domain mutations go through owning services. Model relationships may refer
to existing owners without cloning entities. A service can coordinate work across
owners, but must not absorb their rules or modify their models directly.
Read collaboration also uses services; future reporting access contracts remain to
be designed. Do not create a universal repository or a second ORM to bypass this boundary.

## Avoid duplicate concepts

- Identity owns organizations for employers, providers, ANETI and ministry alike.
- Candidates owns profiles, CV versions and their analysis; documents owns generic
  file metadata; object storage contains bytes. Technical parsing is outside both.
- Taxonomy owns skill/language/education-level definitions; candidate, offer and
  training relationships belong to their respective business domains.
- Matching owns offer_matches and the derived embedding index; training owns
  training_recommendations. Embeddings retain source entity identifiers and do
  not duplicate canonical records. Matching services may coordinate a
  recommendation without owning a duplicate record.
- Assistant owns conversation/action/execution histories; ai/ owns execution.
  Platform owns cross-cutting audit/notification records, not product rules.
- The ANETI AI advisor reuses candidate/CV, matching and training services and
  assistant history. Guidance must not duplicate these records or implement a
  separate agent runtime. ANETI organizations do not imply human advisor accounts.
- Imports owns provenance; recruitment owns imported offers; pipelines/ processes
  data and calls their services. No second job-offer database is introduced.
- Academic education and candidate certifications are candidate data. Training
  delivery and future certificate issuance need separate clarified operations.

## Technical sharing

`backend/common/` must contain domain-neutral helpers only. Shared does not mean
unowned: state and business concepts retain the owner above. Coordinate ownership
changes using the [team workflow](../team/development_workflow.md) and update
[CONTEXT.md](../../CONTEXT.md) and this map together.
