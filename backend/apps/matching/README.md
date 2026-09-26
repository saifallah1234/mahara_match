# matching

**Responsibility:** Matching application services and persisted offer recommendations.

**Logical entity ownership:** offer_matches.

**Sources:** DM §4.C; PDF pp. 5, 9. DM means the root data model; PDF page numbers include the cover.
See the [complete ownership map](../../../docs/architecture/domain_boundaries.md).

Own business-facing comparison/recommendation coordination and offer-match results. AI retrieval/scoring capabilities return results through services. Training owns training_recommendations; never duplicate them here.

## Current backend

`OfferMatch` stores versioned scores and exposes scoped read-only results. A
candidate sees their own results. Verified recruiters see results for applicants
to their organization's offers; the API does not expose pre-application profile
or CV data through match explanations.

No scoring writer or matching formula is implemented while Q26 weights,
eligibility and explanation rules remain open. No matching migration has been
created. Cross-domain operations use owning services.
