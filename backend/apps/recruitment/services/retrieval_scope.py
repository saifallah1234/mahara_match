"""Job offers an actor may retrieve, and their searchable text.

Candidates see the public catalogue (published, non-deleted offers of verified,
non-deleted organizations). Recruiters see every non-deleted offer of the
organizations they may read, drafts included. Any other actor is refused.
"""

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from django.db.models import QuerySet

from backend.apps.identity.models import RoleCode, User, UserRole
from backend.apps.recruitment.models import JobOffer, OfferSkill
from backend.apps.recruitment.services.contracts import RecruitmentPermissionCode
from backend.apps.recruitment.services.job_offers import (
    list_indexable_job_offers,
    list_job_offers,
)
from backend.apps.recruitment.services.scope import organization_ids_with_permission
from backend.common.exceptions import DomainNotFoundError, DomainPermissionError
from backend.common.retrieval import RetrievalDocument


@dataclass(frozen=True)
class OfferSummary:
    offer_id: UUID
    title: str
    organization: str
    offer_url: str
    status: str
    skills: dict[UUID, str]


def visible_offers(actor: User) -> QuerySet[JobOffer]:
    if not actor.is_active:
        raise DomainPermissionError()
    if UserRole.objects.filter(
        user=actor, role__code=RoleCode.CANDIDATE, organization__isnull=True
    ).exists():
        return list_indexable_job_offers()
    scope = organization_ids_with_permission(actor, RecruitmentPermissionCode.READ_OFFERS)
    if not scope:
        # None (unrestricted staff) is out of retrieval scope for this iteration.
        raise DomainPermissionError()
    return list_job_offers(actor)


def retrievable_offers() -> QuerySet[JobOffer]:
    """Offers whose vector may be stored: live offers of verified, live organizations.

    Drafts are included because their organization's recruiters may search them; no
    scope can reach an unverified organization's offers. Reads still pre-filter by scope.
    """
    return JobOffer.objects.filter(
        deleted_at__isnull=True,
        organization__deleted_at__isnull=True,
        organization__verification_status="VERIFIED",
    ).order_by("id")


def offer_documents(offers: QuerySet[JobOffer]) -> list[RetrievalDocument]:
    documents = []
    for offer in offers.select_related("organization").prefetch_related("offer_skills__skill"):
        required_skills = ", ".join(link.skill.canonical_name for link in offer.offer_skills.all())
        text = "\n".join(
            part
            for part in (
                offer.title,
                offer.description,
                offer.contract_type,
                offer.work_mode,
                offer.experience_level,
                offer.governorate,
                offer.city,
                offer.organization.legal_name,
                required_skills,
            )
            if part
        )
        documents.append(RetrievalDocument("offer", offer.id, text, offer.title))
    return documents


def offer_ids_for_skills(offers: QuerySet[JobOffer], skill_ids: Iterable[UUID]) -> Counter[UUID]:
    """How many of ``skill_ids`` each in-scope offer requires."""
    links = OfferSkill.objects.filter(offer__in=offers, skill_id__in=list(skill_ids))
    return Counter(offer_id for (offer_id,) in links.values_list("offer_id"))


def offer_summaries(offers: QuerySet[JobOffer], offer_ids: Iterable[UUID]) -> list[OfferSummary]:
    """Title, organization, link and required skills of in-scope offers, in ``offer_ids`` order."""
    wanted = list(offer_ids)
    by_id = {
        offer.id: offer
        for offer in offers.filter(id__in=wanted)
        .select_related("organization")
        .prefetch_related("offer_skills__skill")
    }
    return [
        OfferSummary(
            offer_id=offer.id,
            title=offer.title,
            organization=offer.organization.legal_name,
            offer_url=offer.offer_url or "",
            status=offer.status,
            skills=dict(
                sorted(
                    (
                        (link.skill_id, link.skill.canonical_name)
                        for link in offer.offer_skills.all()
                    ),
                    key=lambda item: item[1].casefold(),
                )
            ),
        )
        for offer_id in wanted
        if (offer := by_id.get(offer_id)) is not None
    ]


def get_offer_summary(actor: User, offer_id: UUID | str) -> OfferSummary:
    """One offer, or not-found when it is outside the actor's scope."""
    try:
        parsed = UUID(str(offer_id))
    except ValueError as exc:
        raise DomainNotFoundError("Job offer not found.") from exc
    found = offer_summaries(visible_offers(actor), [parsed])
    if not found:
        raise DomainNotFoundError("Job offer not found.")
    return found[0]


_UUID = re.compile(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}")


def offer_reference(actor: User, text: str) -> str | None:
    """The offer a request points at: a UUID in the text, else the longest in-scope title it
    contains. A UUID is returned as written, even when out of scope, so the caller can
    refuse it without revealing whether it exists."""
    if match := _UUID.search(text):
        return match.group(0)
    folded = " ".join(text.casefold().split())
    titles = sorted(
        (
            (" ".join(title.casefold().split()), offer_id)
            for offer_id, title in visible_offers(actor).values_list("id", "title")
            if title.strip()
        ),
        key=lambda item: -len(item[0]),
    )
    return next((str(offer_id) for title, offer_id in titles if title in folded), None)
