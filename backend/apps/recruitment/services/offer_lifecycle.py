from uuid import UUID

from django.db import transaction
from django.utils import timezone

from backend.apps.identity.models import RoleCode, User
from backend.apps.identity.models.organizations import VerificationStatus
from backend.apps.identity.services.access import require_permission
from backend.apps.identity.services.contracts import ORGANIZATION_ROLE_TYPES
from backend.apps.recruitment.models import JobOffer, JobOfferStatus
from backend.apps.recruitment.services.contracts import RecruitmentPermissionCode
from backend.common.exceptions import DomainNotFoundError, DomainValidationError

_NEXT = {
    JobOfferStatus.DRAFT: {JobOfferStatus.PUBLISHED, JobOfferStatus.ARCHIVED},
    JobOfferStatus.PUBLISHED: {JobOfferStatus.PAUSED, JobOfferStatus.CLOSED},
    JobOfferStatus.PAUSED: {JobOfferStatus.PUBLISHED, JobOfferStatus.CLOSED},
    JobOfferStatus.CLOSED: {JobOfferStatus.ARCHIVED},
}


@transaction.atomic
def transition_offer(actor: User, offer_id: UUID, target: str) -> JobOffer:
    try:
        offer = (
            JobOffer.objects.select_for_update()
            .select_related("organization")
            .get(id=offer_id, deleted_at__isnull=True)
        )
    except JobOffer.DoesNotExist as exc:
        raise DomainNotFoundError("Job offer not found.") from exc
    require_permission(actor, RecruitmentPermissionCode.MANAGE_OFFERS, offer.organization_id)
    if target not in _NEXT.get(offer.status, set()):
        raise DomainValidationError(details={"status": ["Invalid offer transition."]})
    if target == JobOfferStatus.PUBLISHED:
        if (
            offer.organization.deleted_at
            or offer.organization.verification_status != VerificationStatus.VERIFIED
            or offer.organization.type not in ORGANIZATION_ROLE_TYPES[RoleCode.RECRUITER]
        ):
            raise DomainValidationError(
                details={"organization_id": ["A verified company is required."]}
            )
        if (
            not offer.title.strip()
            or not offer.description.strip()
            or not offer.offer_skills.exists()
        ):
            raise DomainValidationError(
                details={"offer": ["Title, description and a skill are required."]}
            )
        if offer.application_deadline and offer.application_deadline < timezone.localdate():
            raise DomainValidationError(details={"application_deadline": ["Deadline has passed."]})
        if not offer.easy_apply and not offer.offer_url:
            raise DomainValidationError(
                details={"offer_url": ["External applications need a link."]}
            )
        offer.published_at = offer.published_at or timezone.now()
    if target == JobOfferStatus.CLOSED:
        offer.closed_at = timezone.now()
    offer.status = target
    offer.save(update_fields=["status", "published_at", "closed_at", "updated_at"])
    return offer
