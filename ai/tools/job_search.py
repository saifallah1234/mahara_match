"""Candidate tool: hybrid retrieval over the offers a candidate may see, then explanation.

Retrieval picks and orders the offers. Matched and missing skills are computed
against the candidate's own profile, and missing skills hop to active training
programs. Nothing is persisted as an ``OfferMatch``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from ai.graphrag.missing_skill_training import training_for_missing_skills
from ai.llm.providers.embeddings import embed_query, embedding_config
from ai.retrieval.hybrid.retriever import Embedder, retrieve
from backend.apps.matching.services.retrieval import candidate_offer_search
from backend.apps.recruitment.services.retrieval_scope import offer_summaries, visible_offers

if TYPE_CHECKING:
    from backend.apps.identity.models import User

TOOL_NAME = "search_jobs_for_candidate"
RESULT_LIMIT = 5
TRAININGS_PER_OFFER = 2


def search_jobs_for_candidate(
    actor: User,
    question: str,
    *,
    limit: int = RESULT_LIMIT,
    trainings_per_offer: int = TRAININGS_PER_OFFER,
    embedder: Embedder | None = None,
) -> dict[str, Any]:
    search = candidate_offer_search(actor, question, embedding_config().model)
    result = retrieve(question, search, embedder=embedder or embed_query)
    own_skills = set(search.profile_skill_ids)
    offer_ids = [
        UUID(entity_id) for entity_type, entity_id in result.ranked if entity_type == "offer"
    ]

    matches = []
    for rank, offer in enumerate(offer_summaries(visible_offers(actor), offer_ids[:limit]), 1):
        missing_ids = [skill_id for skill_id in offer.skills if skill_id not in own_skills]
        matches.append(
            {
                "offer_id": str(offer.offer_id),
                "rank": rank,
                "leg_ranks": result.ranks_for(("offer", str(offer.offer_id))),
                "title": offer.title,
                "organization": offer.organization,
                "offer_url": offer.offer_url,
                "matched_skills": [
                    name for skill_id, name in offer.skills.items() if skill_id in own_skills
                ],
                "missing_skills": [offer.skills[skill_id] for skill_id in missing_ids],
                "offer_skills": list(offer.skills.values()),
                "training": training_for_missing_skills(missing_ids, trainings_per_offer),
            }
        )

    if matches:
        reason = "matches_found"
    elif own_skills:
        reason = "no_matching_offers"
    else:
        reason = "candidate_has_no_skills"
    return {
        "reason": reason,
        "profile_has_skills": bool(own_skills),
        "vector_unavailable": result.vector_unavailable,
        "legs": sorted(result.legs),
        "latency_ms": result.latency_ms,
        "matches": matches,
    }
