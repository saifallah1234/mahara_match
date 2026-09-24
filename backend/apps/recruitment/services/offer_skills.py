from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import has_permission, require_permission
from backend.apps.recruitment.models import JobOffer, JobOfferStatus, OfferSkill
from backend.apps.recruitment.services.contracts import RecruitmentPermissionCode
from backend.apps.recruitment.services.job_offers import get_job_offer
from backend.apps.recruitment.services.scope import restrict_to_organizations
from backend.common.exceptions import DomainNotFoundError, DomainValidationError

# offer and skill are fixed once the link exists; only the requirement details change.
_EDITABLE_FIELDS = ("importance", "required_level", "is_mandatory")


def list_offer_skills(actor: User, offer_id: UUID | None = None) -> QuerySet[OfferSkill]:
    queryset = restrict_to_organizations(
        actor,
        OfferSkill.objects.filter(offer__deleted_at__isnull=True),
        RecruitmentPermissionCode.READ_OFFERS,
        "offer__organization_id",
    )
    if offer_id is not None:
        queryset = queryset.filter(offer_id=offer_id)
    return queryset.order_by("created_at", "id")


def get_offer_skill(actor: User, offer_skill_id: UUID | str) -> OfferSkill:
    try:
        offer_skill = OfferSkill.objects.select_related("offer").get(
            id=offer_skill_id, offer__deleted_at__isnull=True
        )
    except OfferSkill.DoesNotExist as exc:
        raise DomainNotFoundError("Offer skill not found.") from exc
    if not has_permission(
        actor, RecruitmentPermissionCode.READ_OFFERS, offer_skill.offer.organization_id
    ):
        raise DomainNotFoundError("Offer skill not found.")
    return offer_skill


@transaction.atomic
def create_offer_skill(actor: User, data: Mapping[str, Any]) -> OfferSkill:
    try:
        offer = get_job_offer(actor, data["offer_id"])
    except DomainNotFoundError as exc:
        raise DomainValidationError(details={"offer_id": ["Offer not found."]}) from exc
    require_permission(actor, RecruitmentPermissionCode.MANAGE_OFFERS, offer.organization_id)

    skill_model = cast(Any, OfferSkill._meta.get_field("skill")).related_model
    if not skill_model.objects.filter(pk=data["skill_id"]).exists():
        raise DomainValidationError(details={"skill_id": ["Skill not found."]})

    fields = {field: data[field] for field in _EDITABLE_FIELDS if field in data}
    try:
        return OfferSkill.objects.create(offer=offer, skill_id=data["skill_id"], **fields)
    except IntegrityError as exc:
        raise DomainValidationError(
            details={"skill_id": ["This skill is already attached to the offer."]}
        ) from exc


@transaction.atomic
def update_offer_skill(actor: User, offer_skill: OfferSkill, data: Mapping[str, Any]) -> OfferSkill:
    require_permission(
        actor, RecruitmentPermissionCode.MANAGE_OFFERS, offer_skill.offer.organization_id
    )
    fields = {field: data[field] for field in _EDITABLE_FIELDS if field in data}
    if not fields:
        return offer_skill
    for field, value in fields.items():
        setattr(offer_skill, field, value)
    offer_skill.save(update_fields=[*fields, "updated_at"])
    return offer_skill


@transaction.atomic
def remove_offer_skill(actor: User, offer_skill: OfferSkill) -> None:
    require_permission(
        actor, RecruitmentPermissionCode.MANAGE_OFFERS, offer_skill.offer.organization_id
    )
    # DM section 7: a published offer must keep at least one skill.
    offer = JobOffer.objects.select_for_update().get(id=offer_skill.offer_id)
    remaining = OfferSkill.objects.filter(offer=offer).count()
    if offer.status == JobOfferStatus.PUBLISHED and remaining <= 1:
        raise DomainValidationError(
            details={"offer_skill": ["A published offer needs at least one skill."]}
        )
    offer_skill.delete()
