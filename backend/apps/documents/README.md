# documents

**Responsibility:** Shared uploaded-file metadata, ownership, storage references and processing status.

**Logical entity ownership:** documents.

**Sources:** DM §§4.B, 4.F, 5; PDF p. 9. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Own file metadata, not CV versions or import histories. Object storage holds bytes; extraction/OCR belongs in pipelines/document_processing/.

## Reserved boundaries

- `api/`: owner-scoped read transport.
- `services/`: trusted metadata creation and ownership checks.
- `models/`: Django ORM metadata definition.

The initial migration is applied. Binary upload and storage adapters remain
future work.
Cross-domain operations use the owning service; do not duplicate entities or mutate
another domain's models directly. Open requirements are tracked in the
[question register](../../../docs/architecture/open_questions.md).
