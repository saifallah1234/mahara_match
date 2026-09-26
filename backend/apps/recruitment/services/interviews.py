from uuid import UUID

from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import has_permission
from backend.apps.recruitment.models import Interview
from backend.apps.recruitment.services.contracts import RecruitmentPermissionCode
from backend.apps.recruitment.services.scope import restrict_to_organizations
from backend.common.exceptions import DomainNotFoundError

# Read-only in Phase 1: scheduling and feedback need lifecycle permissions (Q12, P05-3).
# TODO(G03): `feedback` is internal recruiter text; candidate visibility is undecided.


def list_interviews(actor: User, application_id: UUID | None = None) -> QuerySet[Interview]:
    queryset = restrict_to_organizations(
        actor,
        Interview.objects.all(),
        RecruitmentPermissionCode.READ_INTERVIEWS,
        "application__offer__organization_id",
    )
    if application_id is not None:
        queryset = queryset.filter(application_id=application_id)
    return queryset.order_by("scheduled_at", "id")


def get_interview(actor: User, interview_id: UUID | str) -> Interview:
    try:
        interview = Interview.objects.select_related("application__offer").get(id=interview_id)
    except Interview.DoesNotExist as exc:
        raise DomainNotFoundError("Interview not found.") from exc
    if not has_permission(
        actor,
        RecruitmentPermissionCode.READ_INTERVIEWS,
        interview.application.offer.organization_id,
    ):
        raise DomainNotFoundError("Interview not found.")
    return interview
