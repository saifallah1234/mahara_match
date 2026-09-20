# Persistence strategy

Sources: [DM](../../mahara_match_data_modeling.md) §§1, 3–7, 9 and
[PDF](../../Cahier%20de%20charge%20pr%C3%A9liminaire%20PDF.pdf) physical p. 9.

| Store | Authority and contents |
| --- | --- |
| PostgreSQL | Canonical accounts, profiles, organizations, offers, applications, training, histories and metadata |
| Object storage | CVs, images, certificates, logos and raw import files; metadata/URIs remain relational |
| Vector index | Derived embeddings linked to PostgreSQL identifiers |
| Neo4j | Derived relationships used for graph retrieval and explanations |

The future Django ORM is the only relational schema authority. Models and Django
migrations are introduced with implementation, not scaffolded SQL. The logical
table dictionary is an input to that design, not executable DDL or a demand to
create one app per table. No database or migration has been created.

DM §1 proposes UUID primary keys and business timestamps, while association tables
use composite keys and global roles allow null organization scope. Resolve Q06
before physical modeling; do not silently choose keys or translate password_hash
into custom authentication storage.

DM §7 specifies case-insensitive unique email, unique candidate/offer applications,
unique candidate/session enrollment, bounded scores, date/salary consistency,
publication requirements, at most one primary CV and history-aware deletion.
These remain requirements for future service/model design. Status transitions,
retention, currency and visibility details remain open; no constraints are
implemented in this scaffold.

Validated canonical changes are written to PostgreSQL first and projected with
idempotent synchronization (DM §5). Derived stores must not become alternate
transactional authorities. Freshness targets, retry/delete propagation and rebuild
policies need decisions before pipeline implementation.

Candidate confirmation is required for extracted profile data. DM §4.B allows
raw/semi-structured parsed_data_json, while PDF p. 9 says extracted information
must be confirmed before recording: Q08 tracks the staging/persistence ambiguity.

Migration coordination is documented in the [team workflow](../team/development_workflow.md).
Never exclude future migrations from version control or maintain parallel SQL schemas.
