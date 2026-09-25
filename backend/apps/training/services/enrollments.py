from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db.models import QuerySet
from django.utils import timezone

from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.training.models import EnrollmentStatus, TrainingEnrollment, TrainingSession
from backend.apps.training.services.contracts import TrainingPermissionCode
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


class EnrollmentLimitReachedError(DomainValidationError):
    code = "training_session_full"
    default_message = "Cannot enroll candidate: session capacity reached."


class DuplicateEnrollmentError(DomainValidationError):
    code = "training_duplicate_enrollment"
    default_message = "Candidate is already enrolled in this session."


def _require_self_or_manage(actor: User, candidate_id: UUID | str) -> None:
    if str(candidate_id) == str(actor.id):
        require_permission(actor, TrainingPermissionCode.ENROLL_SELF)
    else:
        require_permission(actor, TrainingPermissionCode.MANAGE_ENROLLMENTS)


def list_enrollments(
    actor: User, candidate_id: UUID | str | None = None
) -> QuerySet[TrainingEnrollment]:
    if candidate_id is None or str(candidate_id) == str(actor.id):
        require_permission(actor, TrainingPermissionCode.VIEW_OWN_ENROLLMENTS)
        return TrainingEnrollment.objects.filter(candidate_id=candidate_id or actor.id)
    require_permission(actor, TrainingPermissionCode.MANAGE_ENROLLMENTS)
    return TrainingEnrollment.objects.filter(candidate_id=candidate_id)


def get_enrollment(actor: User, enrollment_id: UUID | str) -> TrainingEnrollment:
    try:
        enrollment = TrainingEnrollment.objects.select_related("session__program").get(
            id=enrollment_id
        )
    except TrainingEnrollment.DoesNotExist as exc:
        raise DomainNotFoundError("Enrollment not found.") from exc

    if str(enrollment.candidate_id) == str(actor.id):
        require_permission(actor, TrainingPermissionCode.VIEW_OWN_ENROLLMENTS)
    else:
        require_permission(actor, TrainingPermissionCode.MANAGE_ENROLLMENTS)
    return enrollment


def enroll_candidate(actor: User, data: Mapping[str, Any]) -> TrainingEnrollment:
    candidate_id = data.get("candidate_id", actor.id)
    _require_self_or_manage(actor, candidate_id)

    try:
        session = TrainingSession.objects.get(id=data["session_id"])
    except TrainingSession.DoesNotExist as exc:
        raise DomainNotFoundError("Training session not found.") from exc

    current_count = TrainingEnrollment.objects.filter(session_id=session.id).count()
    if current_count >= session.capacity:
        raise EnrollmentLimitReachedError()

    if TrainingEnrollment.objects.filter(session_id=session.id, candidate_id=candidate_id).exists():
        raise DuplicateEnrollmentError()

    return TrainingEnrollment.objects.create(
        session=session,
        candidate_id=candidate_id,
        status=EnrollmentStatus.REGISTERED,
    )


def update_progress(
    actor: User, enrollment: TrainingEnrollment, completion_rate: float
) -> TrainingEnrollment:
    require_permission(
        actor,
        TrainingPermissionCode.MANAGE_ENROLLMENTS,
        organization_id=enrollment.session.program.organization_id,
    )
    enrollment.completion_rate = completion_rate
    if completion_rate >= 100.0:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = timezone.now()
    elif completion_rate > 0.0 and enrollment.status == EnrollmentStatus.REGISTERED:
        enrollment.status = EnrollmentStatus.IN_PROGRESS
    enrollment.save(update_fields=["completion_rate", "status", "completed_at", "updated_at"])
    return enrollment


def cancel_enrollment(actor: User, enrollment: TrainingEnrollment) -> TrainingEnrollment:
    _require_self_or_manage(actor, enrollment.candidate_id)
    enrollment.status = EnrollmentStatus.DROPPED
    enrollment.save(update_fields=["status", "updated_at"])
    return enrollment
