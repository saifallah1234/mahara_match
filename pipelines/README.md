# Data processing and orchestration boundaries

| Directory | Future responsibility |
| --- | --- |
| `ingestion/` | Authorized partner/API/file acquisition and import processing |
| `document_processing/extraction/` | Direct extraction from text-bearing PDFs |
| `document_processing/ocr/` | Scanned/image document preprocessing and OCR |
| `normalization/` | Reusable cleanup and canonical skill mapping |
| `quality/` | Data checks and rejection reporting |
| `synchronization/` | Derived vector and Neo4j projection synchronization |
| `maintenance/` | Deduplication and archival processing with approved rules |
| `dagster/` | Future assets, jobs, resources, schedules and sensors |

Dagster definitions coordinate reusable processing; they do not own business
models. Processing uses application services for relational reads and writes.
Embedding computation reuses `ai/embeddings/`, avoiding a second implementation.
Do not introduce schedules, retry policies or retention rules before they are agreed.

See [orchestration](../docs/workflows/orchestration.md).
