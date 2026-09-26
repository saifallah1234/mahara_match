from uuid import UUID

from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.recruitment.models import ApplicationStatusHistory
from backend.apps.recruitment.services.applications import list_applications
from backend.common.exceptions import DomainNotFoundError


def list_status_history(
    actor: User, application_id: UUID | None = None
) -> QuerySet[ApplicationStatusHistory]:
    queryset = ApplicationStatusHistory.objects.filter(application__in=list_applications(actor))
    if application_id is not None:
        queryset = queryset.filter(application_id=application_id)
    return queryset.order_by("changed_at", "id")


def get_status_history_entry(actor: User, entry_id: UUID | str) -> ApplicationStatusHistory:
    try:
        entry = list_status_history(actor).get(id=entry_id)
    except ApplicationStatusHistory.DoesNotExist as exc:
        raise DomainNotFoundError("Status history entry not found.") from exc
    return entry
