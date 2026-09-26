from uuid import UUID

from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import has_permission
from backend.apps.recruitment.models import Application
from backend.apps.recruitment.services.contracts import RecruitmentPermissionCode
from backend.apps.recruitment.services.scope import restrict_to_organizations
from backend.common.exceptions import DomainNotFoundError

# Read-only in Phase 1: submission, withdrawal and status changes belong to P05-3.
# TODO(G03): candidates reading their own applications needs the user -> candidate link.


def list_applications(actor: User) -> QuerySet[Application]:
    queryset = restrict_to_organizations(
        actor,
        Application.objects.all(),
        RecruitmentPermissionCode.READ_APPLICATIONS,
        "offer__organization_id",
    )
    return queryset.order_by("created_at", "id")


def get_application(actor: User, application_id: UUID | str) -> Application:
    try:
        application = Application.objects.select_related("offer").get(id=application_id)
    except Application.DoesNotExist as exc:
        raise DomainNotFoundError("Application not found.") from exc
    if not has_permission(
        actor, RecruitmentPermissionCode.READ_APPLICATIONS, application.offer.organization_id
    ):
        raise DomainNotFoundError("Application not found.")
    return application
