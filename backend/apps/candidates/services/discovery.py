from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet

from backend.apps.candidates.models import CandidateProfile, ProfileVisibility
from backend.apps.candidates.services.contracts import CandidatePermissionCode
from backend.apps.identity.models import OrganizationType, RoleCode, User, UserRole, UserStatus
from backend.apps.identity.models.organizations import VerificationStatus
from backend.common.exceptions import DomainNotFoundError, DomainPermissionError


def list_candidates(actor: User) -> QuerySet[CandidateProfile]:
    if (
        not actor.is_active
        or not UserRole.objects.filter(
            user=actor,
            role__code=RoleCode.RECRUITER,
            role__permission_grants__permission__code=CandidatePermissionCode.DISCOVER,
            organization__members__user=actor,
            organization__type__in=(OrganizationType.COMPANY, OrganizationType.SUBSIDIARY),
            organization__verification_status=VerificationStatus.VERIFIED,
            organization__deleted_at__isnull=True,
        ).exists()
    ):
        raise DomainPermissionError()
    return (
        CandidateProfile.objects.filter(
            profile_visibility=ProfileVisibility.RECRUITERS,
            user__status=UserStatus.ACTIVE,
            user__deleted_at__isnull=True,
        )
        .prefetch_related("skills", "experiences", "educations")
        .select_related("preferences")
        .order_by("id")
    )


def filter_candidates(
    queryset: QuerySet[CandidateProfile], filters: Mapping[str, Any]
) -> QuerySet[CandidateProfile]:
    lookups = {
        "skill": "skills__skill_id",
        "education_level": "educations__education_level_id",
        "governorate": "governorate__iexact",
        "work_mode": "preferences__work_mode",
        "relocation": "preferences__relocation",
    }
    for name, lookup in lookups.items():
        if name in filters:
            queryset = queryset.filter(**{lookup: filters[name]})
    if search := filters.get("search"):
        queryset = queryset.filter(
            Q(headline__icontains=search)
            | Q(skills__skill__canonical_name__icontains=search)
            | Q(experiences__job_title__icontains=search)
        )
    return queryset.distinct()


def get_candidate(actor: User, candidate_id: UUID | str) -> CandidateProfile:
    try:
        return list_candidates(actor).get(pk=candidate_id)
    except (CandidateProfile.DoesNotExist, ValidationError) as exc:
        raise DomainNotFoundError("Candidate profile not found.") from exc
