# documents

**Future responsibility:** Shared uploaded-file metadata, ownership, storage references and processing status.

**Logical entity ownership:** documents.

**Sources:** DM §§4.B, 4.F, 5; PDF p. 9. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Own file metadata, not CV versions or import histories. Object storage holds bytes; extraction/OCR belongs in pipelines/document_processing/.

## Reserved boundaries

- `api/`: future DRF transport, request validation and response representation.
- `services/`: application operations, authorization and business coordination.
- `models/`: future Django ORM definitions owned by this domain.

These directories contain no implementations. No Django app has been initialized.
Cross-domain operations use the owning service; do not duplicate entities or mutate
another domain's models directly. Open requirements are tracked in the
[question register](../../../docs/architecture/open_questions.md).
