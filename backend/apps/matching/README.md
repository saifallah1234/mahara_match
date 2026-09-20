# matching

**Future responsibility:** Matching application services and persisted offer recommendations.

**Logical entity ownership:** offer_matches.

**Sources:** DM §4.C; PDF pp. 5, 9. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Own business-facing comparison/recommendation coordination and offer-match results. AI retrieval/scoring capabilities return results through services. Training owns training_recommendations; never duplicate them here.

## Reserved boundaries

- `api/`: future DRF transport, request validation and response representation.
- `services/`: application operations, authorization and business coordination.
- `models/`: future Django ORM definitions owned by this domain.

These directories contain no implementations. No Django app has been initialized.
Cross-domain operations use the owning service; do not duplicate entities or mutate
another domain's models directly. Open requirements are tracked in the
[question register](../../../docs/architecture/open_questions.md).
