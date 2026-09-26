from uuid import UUID

from django.db.models import Q, QuerySet

from backend.apps.identity.models import RoleCode, User, UserRole
from backend.apps.recruitment.models import Interview
from backend.apps.recruitment.services.contracts import RecruitmentPermissionCode
from backend.apps.recruitment.services.scope import organization_ids_with_permission
from backend.common.exceptions import DomainNotFoundError, DomainPermissionError


def list_interviews(actor: User, application_id: UUID | None = None) -> QuerySet[Interview]:
    scope = organization_ids_with_permission(actor, RecruitmentPermissionCode.READ_INTERVIEWS)
    candidate = (
        actor.is_active
        and UserRole.objects.filter(user=actor, role__code=RoleCode.CANDIDATE).exists()
    )
    if scope is None:
        queryset = Interview.objects.all()
    else:
        if not candidate and not scope:
            raise DomainPermissionError()
        visibility = Q(
            application__offer__organization_id__in=scope,
            application__candidate__user__status="ACTIVE",
            application__offer__organization__deleted_at__isnull=True,
            application__offer__organization__verification_status="VERIFIED",
        )
        if candidate:
            visibility |= Q(application__candidate__user=actor)
        queryset = Interview.objects.filter(visibility)
    if application_id is not None:
        queryset = queryset.filter(application_id=application_id)
    return queryset.order_by("scheduled_at", "id")


def get_interview(actor: User, interview_id: UUID | str) -> Interview:
    try:
        interview = list_interviews(actor).select_related("application__offer").get(id=interview_id)
    except Interview.DoesNotExist as exc:
        raise DomainNotFoundError("Interview not found.") from exc
    return interview
