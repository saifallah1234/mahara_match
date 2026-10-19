"""Recruiter tools: opted-in limited candidate profiles, and the recruiter's own offers.

Privacy: candidate-search evidence holds profile IDs, ranks, leg ranks and matched skill
names only. Limited-profile fields are read live (in scope) to compute the matched skills
and are never returned, so they cannot reach the tool trace or assistant history.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from ai.llm.providers.embeddings import embed_query, embedding_config
from ai.retrieval.hybrid.retriever import Embedder, retrieve
from backend.apps.candidates.services.retrieval_scope import limited_profile_view
from backend.apps.matching.services.retrieval import (
    recruiter_offer_search,
    recruiter_profile_search,
    skill_is_mentioned,
)
from backend.apps.recruitment.services.retrieval_scope import (
    get_offer_summary,
    offer_summaries,
    visible_offers,
)
from backend.common.exceptions import DomainNotFoundError

if TYPE_CHECKING:
    from backend.apps.identity.models import User

CANDIDATE_TOOL_NAME = "search_candidates"
OFFER_TOOL_NAME = "search_own_offers"
RESULT_LIMIT = 5


def search_candidates(
    actor: User,
    question: str,
    offer_id: str | None = None,
    *,
    limit: int = RESULT_LIMIT,
    embedder: Embedder | None = None,
) -> dict[str, Any]:
    query = question
    seed_skill_ids: list[UUID] = []
    seed_names: set[str] = set()
    if offer_id is not None:
        try:
            offer = get_offer_summary(actor, offer_id)
        except DomainNotFoundError:
            # Same answer whether the offer is elsewhere or does not exist.
            return {"reason": "offer_not_accessible", "offer_id": None, "matches": []}
        query = "\n".join([question, offer.title, ", ".join(offer.skills.values())])
        seed_skill_ids = list(offer.skills)
        seed_names = set(offer.skills.values())

    search = recruiter_profile_search(actor, query, embedding_config().model, seed_skill_ids)
    result = retrieve(query, search, embedder=embedder or embed_query)
    profile_ids = [
        UUID(entity_id)
        for entity_type, entity_id in result.ranked
        if entity_type == "candidate_profile"
    ][:limit]

    matches = []
    for rank, view in enumerate(limited_profile_view(actor, profile_ids), 1):
        matched = [
            name
            for name in view["skills"]
            if name in seed_names or skill_is_mentioned(question, name)
        ]
        matches.append(
            {
                "profile_id": view["id"],
                "rank": rank,
                "leg_ranks": result.ranks_for(("candidate_profile", view["id"])),
                "matched_skills": matched,
            }
        )
    return {
        "reason": "profiles_found" if matches else "no_matching_profiles",
        "offer_id": offer_id,
        "vector_unavailable": result.vector_unavailable,
        "legs": sorted(result.legs),
        "latency_ms": result.latency_ms,
        "matches": matches,
    }


def search_own_offers(
    actor: User,
    question: str,
    *,
    limit: int = RESULT_LIMIT,
    embedder: Embedder | None = None,
) -> dict[str, Any]:
    if not visible_offers(actor).exists():
        return {"reason": "recruiter_has_no_offers", "matches": []}
    search = recruiter_offer_search(actor, question, embedding_config().model)
    result = retrieve(question, search, embedder=embedder or embed_query)
    offer_ids = [
        UUID(entity_id) for entity_type, entity_id in result.ranked if entity_type == "offer"
    ]
    matches = [
        {
            "offer_id": str(offer.offer_id),
            "rank": rank,
            "leg_ranks": result.ranks_for(("offer", str(offer.offer_id))),
            "title": offer.title,
            "status": offer.status,
            "skills": list(offer.skills.values()),
        }
        for rank, offer in enumerate(offer_summaries(visible_offers(actor), offer_ids[:limit]), 1)
    ]
    return {
        "reason": "offers_found" if matches else "no_matching_offers",
        "vector_unavailable": result.vector_unavailable,
        "legs": sorted(result.legs),
        "latency_ms": result.latency_ms,
        "matches": matches,
    }
