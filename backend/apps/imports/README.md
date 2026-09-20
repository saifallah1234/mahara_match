# imports

**Future responsibility:** Source authorization metadata and traceable ingestion records.

**Logical entity ownership:** data_sources, import_batches, import_rows.

**Sources:** DM §§3.3, 4.F; PDF pp. 6, 10. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Processing lives in pipelines/. Recruitment owns resulting offers; documents owns retained raw-file metadata. Source-specific deduplication rules must be clarified before implementation.

## Reserved boundaries

- `api/`: future DRF transport, request validation and response representation.
- `services/`: application operations, authorization and business coordination.
- `models/`: future Django ORM definitions owned by this domain.

These directories contain no implementations. No Django app has been initialized.
Cross-domain operations use the owning service; do not duplicate entities or mutate
another domain's models directly. Open requirements are tracked in the
[question register](../../../docs/architecture/open_questions.md).
