from uuid import UUID

from django.db.models import Q, QuerySet

from backend.apps.identity.models import RoleCode, User, UserRole
from backend.apps.recruitment.models import Application
from backend.apps.recruitment.services.contracts import RecruitmentPermissionCode
from backend.apps.recruitment.services.scope import organization_ids_with_permission
from backend.common.exceptions import DomainNotFoundError, DomainPermissionError


def list_applications(actor: User) -> QuerySet[Application]:
    scope = organization_ids_with_permission(actor, RecruitmentPermissionCode.READ_APPLICATIONS)
    if scope is None:
        return Application.objects.order_by("created_at", "id")
    candidate = (
        actor.is_active
        and UserRole.objects.filter(user=actor, role__code=RoleCode.CANDIDATE).exists()
    )
    if not candidate and not scope:
        raise DomainPermissionError()
    visibility = Q(
        offer__organization_id__in=scope,
        candidate__user__status="ACTIVE",
        offer__organization__deleted_at__isnull=True,
        offer__organization__verification_status="VERIFIED",
    )
    if candidate:
        visibility |= Q(candidate__user=actor)
    return Application.objects.filter(visibility).order_by("created_at", "id")


def get_application(actor: User, application_id: UUID | str) -> Application:
    try:
        application = list_applications(actor).select_related("offer").get(id=application_id)
    except Application.DoesNotExist as exc:
        raise DomainNotFoundError("Application not found.") from exc
    return application
