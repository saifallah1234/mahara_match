from uuid import UUID

from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import has_permission
from backend.apps.recruitment.models import ApplicationStatusHistory
from backend.apps.recruitment.services.contracts import RecruitmentPermissionCode
from backend.apps.recruitment.services.scope import restrict_to_organizations
from backend.common.exceptions import DomainNotFoundError

# Append-only: entries are written by the transition service (P05-3), never by callers.


def list_status_history(
    actor: User, application_id: UUID | None = None
) -> QuerySet[ApplicationStatusHistory]:
    queryset = restrict_to_organizations(
        actor,
        ApplicationStatusHistory.objects.all(),
        RecruitmentPermissionCode.READ_APPLICATIONS,
        "application__offer__organization_id",
    )
    if application_id is not None:
        queryset = queryset.filter(application_id=application_id)
    return queryset.order_by("changed_at", "id")


def get_status_history_entry(actor: User, entry_id: UUID | str) -> ApplicationStatusHistory:
    try:
        entry = ApplicationStatusHistory.objects.select_related("application__offer").get(
            id=entry_id
        )
    except ApplicationStatusHistory.DoesNotExist as exc:
        raise DomainNotFoundError("Status history entry not found.") from exc
    if not has_permission(
        actor,
        RecruitmentPermissionCode.READ_APPLICATIONS,
        entry.application.offer.organization_id,
    ):
        raise DomainNotFoundError("Status history entry not found.")
    return entry
