# imports

**Responsibility:** Source authorization metadata and traceable ingestion records.

**Logical entity ownership:** data_sources, import_batches, import_rows.

**Sources:** DM §§3.3, 4.F; PDF pp. 6, 10. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Processing lives in pipelines/. Recruitment owns resulting offers; documents owns retained raw-file metadata. Recruitment enforces `(source_id, external_id)` uniqueness for imported offers.

## Current backend

Data sources, batches and rows have ORM models. Admin-granted source management
requires separate authorization with evidence, acquisition method and expiry;
source configuration changes revoke authorization. Batch and row writes are
trusted-service only; their API is read-only to users with `imports.record.read`.
Source creation, changes, approval and revocation append a redacted audit record.
Automated API/CSV rows without an external ID are recorded as rejected. Actual
connectors, offer reconciliation and manual-file ownership remain pending. The
initial source/provenance migrations are applied.
