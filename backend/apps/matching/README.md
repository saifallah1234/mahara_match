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

The candidate agent's V1 calculator persists a deterministic `skill-coverage-v1`
score: matched canonical skills divided by all skills attached to a published
offer. Experience and location remain unknown, and a candidate with no recorded
skills receives no scored matches. This is a narrow pilot baseline, not a final
Q26 eligibility or ranking policy. Cross-domain reads use owning services.
