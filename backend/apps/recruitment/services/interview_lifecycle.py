from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.platform.services.records import append_audit, send_notification
from backend.apps.recruitment.models import (
    Application,
    ApplicationStatus,
    Interview,
    InterviewStatus,
    InterviewType,
)
from backend.apps.recruitment.services.contracts import RecruitmentPermissionCode
from backend.common.exceptions import (
    DomainNotFoundError,
    DomainPermissionError,
    DomainValidationError,
)


@transaction.atomic
def schedule_interview(actor: User, data: Mapping[str, Any]) -> Interview:
    try:
        application = (
            Application.objects.select_for_update()
            .select_related("offer__organization", "candidate__user")
            .get(id=data["application_id"])
        )
    except Application.DoesNotExist as exc:
        raise DomainNotFoundError("Application not found.") from exc
    require_permission(
        actor, RecruitmentPermissionCode.MANAGE_INTERVIEWS, application.offer.organization_id
    )
    if application.candidate.user_id == actor.id:
        raise DomainPermissionError("You cannot interview yourself.")
    if (
        application.offer.organization.deleted_at
        or application.offer.organization.verification_status != "VERIFIED"
        or not application.candidate.user.is_active
    ):
        raise DomainPermissionError()
    if not application.offer.easy_apply or application.status != ApplicationStatus.INTERVIEW:
        raise DomainValidationError(
            details={"application_id": ["Application is not in interview stage."]}
        )
    if data["type"] not in InterviewType.values:
        raise DomainValidationError(details={"type": ["Invalid interview type."]})
    if timezone.is_naive(data["scheduled_at"]) or data["scheduled_at"] <= timezone.now():
        raise DomainValidationError(details={"scheduled_at": ["Use a future time."]})
    duration = data.get("duration_minutes")
    if duration is not None and duration < 1:
        raise DomainValidationError(details={"duration_minutes": ["Must be positive."]})
    interview = Interview.objects.create(
        application=application,
        scheduled_by=actor,
        type=data["type"],
        scheduled_at=data["scheduled_at"],
        duration_minutes=duration,
        location_or_url=data.get("location_or_url", ""),
        status=InterviewStatus.SCHEDULED,
    )
    send_notification(
        application.candidate.user,
        type="recruitment.interview.scheduled",
        title="Entretien planifié",
        body=f"Un entretien est planifié pour votre candidature à « {application.offer.title} ».",
        payload_json={"application_id": str(application.id), "interview_id": str(interview.id)},
    )
    return interview


@transaction.atomic
def finish_interview(actor: User, interview_id: UUID, target: str, feedback: str = "") -> Interview:
    try:
        interview = (
            Interview.objects.select_for_update()
            .select_related("application__offer__organization", "application__candidate__user")
            .get(id=interview_id)
        )
    except Interview.DoesNotExist as exc:
        raise DomainNotFoundError("Interview not found.") from exc
    require_permission(
        actor,
        RecruitmentPermissionCode.MANAGE_INTERVIEWS,
        interview.application.offer.organization_id,
    )
    if interview.application.candidate.user_id == actor.id:
        raise DomainPermissionError("You cannot review your own interview.")
    if (
        interview.application.offer.organization.deleted_at
        or interview.application.offer.organization.verification_status != "VERIFIED"
        or not interview.application.candidate.user.is_active
    ):
        raise DomainPermissionError()
    if interview.status != InterviewStatus.SCHEDULED or target not in {
        InterviewStatus.COMPLETED,
        InterviewStatus.CANCELLED,
    }:
        raise DomainValidationError(details={"status": ["Invalid interview transition."]})
    previous_status = interview.status
    interview.status = target
    interview.feedback = feedback if target == InterviewStatus.COMPLETED else ""
    interview.save(update_fields=["status", "feedback", "updated_at"])
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="recruitment.interview.finish",
        entity_type="interview",
        entity_id=interview.id,
        before={"status": previous_status},
        after={"status": target},
    )
    if target == InterviewStatus.CANCELLED:
        send_notification(
            interview.application.candidate.user,
            type="recruitment.interview.cancelled",
            title="Entretien annulé",
            body=f"Votre entretien pour « {interview.application.offer.title} » est annulé.",
            payload_json={
                "application_id": str(interview.application_id),
                "interview_id": str(interview.id),
            },
        )
    return interview
