# Persistence strategy

Sources: [DM](../../mahara_match_data_modeling.md) §§1, 3–7, 9 and
[PDF](../../Cahier%20de%20charge%20pr%C3%A9liminaire%20PDF.pdf) physical p. 9.

| Store | Authority and contents |
| --- | --- |
| PostgreSQL | Canonical accounts, profiles, organizations, offers, applications, training, histories and metadata |
| Object storage | CVs, images, certificates, logos and raw import files; metadata/URIs remain relational |
| PostgreSQL text search | Initial lexical search over authorized relational data |
| pgvector, if selected | Derived embeddings linked to PostgreSQL identifiers |
| Neo4j, if needed | Derived relationships when GraphRAG traversal needs a separate graph store |

The future Django ORM is the only relational schema authority. Models and Django
migrations are introduced with implementation, not scaffolded SQL. The logical
table dictionary is an input to that design, not executable DDL or a demand to
create one app per table. No database or migration has been created.

Q06 now chooses UUID IDs and timestamps for persisted entities, including
associations, with scoped uniqueness. Global role assignments retain separate
conditional uniqueness from organization assignments. Owners still define exact
foreign-key deletion rules. Django `AbstractUser` handles passwords; do not
translate source `password_hash` into separate authentication storage.

DM §7 specifies case-insensitive unique email, unique candidate/offer applications,
unique candidate/session enrollment, bounded scores, date/salary consistency,
publication requirements, at most one primary CV and history-aware deletion.
These remain requirements for future service/model design. Q10 supersedes the
source's currency-field rule: offer salaries are TND only, with no currency column;
non-TND imports cannot be silently relabeled. Main application progression,
private-by-default candidate visibility and opt-in limited recruiter/application
access are agreed. Recruiters see only headline, skills, experience, education,
governorate and work preferences before application; name, contact, birth date
and CV remain hidden. Recruiters may advance or reject active applications,
candidates may withdraw them, and hired/rejected/withdrawn are terminal. CV/account
deletion is soft deletion, with no MVP restoration or scheduled purge. Retained-data
policy still needs review before release.

Validated canonical changes are written to PostgreSQL first and projected with
idempotent synchronization (DM §5). Derived stores must not become alternate
transactional authorities. Imports follow source-specific cadence, failures have
bounded retries and reconciliation is periodic; derived indexes rebuild through
versioned switching. Concrete freshness, retry counts and deletion timing remain
operational contract details.

Candidate confirmation is required for extracted profile data. Raw extraction
stays in a restricted review area; only candidate-approved facts enter normalized
tables. Raw results stay linked to the CV without an age-based deletion timer;
soft-deleted CV content is excluded from normal reads and retrieval.

Migration coordination is documented in the [team workflow](../team/development_workflow.md).
Never exclude future migrations from version control or maintain parallel SQL schemas.
