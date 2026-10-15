"""Deterministic, persisted skill-coverage matches for the candidate agent."""

from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from backend.apps.candidates.models import CandidateSkill
from backend.apps.candidates.services.records import list_records, own_profile
from backend.apps.identity.models import User
from backend.apps.matching.models import OfferMatch
from backend.apps.recruitment.models import JobOfferStatus
from backend.apps.recruitment.services.job_offers import list_job_offers
from backend.apps.recruitment.services.offer_skills import list_offer_skills

MATCHING_VERSION = "skill-coverage-v1"


def candidate_has_skills(actor: User) -> bool:
    return list_records(actor, CandidateSkill).exists()


@transaction.atomic
def calculate_candidate_matches(actor: User) -> list[OfferMatch]:
    """Recalculate and persist skill coverage for the active candidate's visible offers."""
    profile = own_profile(actor)
    candidate_skill_ids = {
        str(skill_id)
        for skill_id in list_records(actor, CandidateSkill).values_list("skill_id", flat=True)
    }
    if not candidate_skill_ids:
        return []

    offers = list_job_offers(actor).filter(
        status=JobOfferStatus.PUBLISHED,
        organization__verification_status="VERIFIED",
        organization__deleted_at__isnull=True,
    )
    skills_by_offer: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for offer_skill in (
        list_offer_skills(actor).filter(offer_id__in=offers.values("id")).select_related("skill")
    ):
        skills_by_offer[str(offer_skill.offer_id)].append(
            (str(offer_skill.skill_id), offer_skill.skill.canonical_name)
        )

    calculated_at = timezone.now()
    matches = []
    for offer in offers.select_related("organization"):
        offer_skills = skills_by_offer.get(str(offer.id), [])
        if not offer_skills:
            continue
        matched = [name for skill_id, name in offer_skills if skill_id in candidate_skill_ids]
        missing = [name for skill_id, name in offer_skills if skill_id not in candidate_skill_ids]
        score = (Decimal(len(matched)) * Decimal("100") / Decimal(len(offer_skills))).quantize(
            Decimal("0.01")
        )
        match, _ = OfferMatch.objects.update_or_create(
            candidate=profile,
            offer=offer,
            model_version=MATCHING_VERSION,
            defaults={
                "overall_score": score,
                "skill_score": score,
                "experience_score": None,
                "location_score": None,
                "calculated_at": calculated_at,
                "explanation_json": {
                    "method": MATCHING_VERSION,
                    "matched_skills": matched,
                    "missing_skills": missing,
                    "offer_skills": [name for _, name in offer_skills],
                    "matched_count": len(matched),
                    "offer_skill_count": len(offer_skills),
                },
            },
        )
        match.offer = offer
        matches.append(match)

    return sorted(
        matches,
        key=lambda item: (-item.overall_score, item.offer.title.casefold(), str(item.id)),
    )
