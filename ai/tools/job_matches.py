from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.apps.matching.services.baseline import (
    calculate_candidate_matches,
    candidate_has_skills,
)

if TYPE_CHECKING:
    from backend.apps.identity.models import User


def get_candidate_job_matches(actor: User) -> dict[str, Any]:
    """Return this candidate's persisted, freshly calculated match evidence."""
    matches = calculate_candidate_matches(actor)
    if matches:
        reason = "matches_found"
    elif candidate_has_skills(actor):
        reason = "no_eligible_offers"
    else:
        reason = "candidate_has_no_skills"
    return {
        "reason": reason,
        "matches": [
            {
                "offer_id": str(match.offer_id),
                "title": match.offer.title,
                "organization": match.offer.organization.legal_name,
                "score": str(match.overall_score),
                "matched_skills": match.explanation_json["matched_skills"],
                "missing_skills": match.explanation_json["missing_skills"],
                "offer_skills": match.explanation_json["offer_skills"],
                "offer_url": match.offer.offer_url,
            }
            for match in matches
        ],
    }
