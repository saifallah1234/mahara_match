from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from backend.apps.candidates.services.records import own_profile
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


def list_enrollments(
    actor: User,
    candidate_id: UUID | str | None = None,
    organization_id: UUID | str | None = None,
) -> QuerySet[TrainingEnrollment]:
    if organization_id is None:
        profile = own_profile(actor)
        require_permission(actor, TrainingPermissionCode.VIEW_OWN_ENROLLMENTS)
        if candidate_id is not None and str(candidate_id) != str(profile.id):
            return TrainingEnrollment.objects.none()
        return TrainingEnrollment.objects.filter(candidate_id=profile.id)
    require_permission(
        actor, TrainingPermissionCode.MANAGE_ENROLLMENTS, organization_id=organization_id
    )
    queryset = TrainingEnrollment.objects.filter(session__program__organization_id=organization_id)
    return queryset.filter(candidate_id=candidate_id) if candidate_id else queryset


def get_enrollment(actor: User, enrollment_id: UUID | str) -> TrainingEnrollment:
    try:
        enrollment = TrainingEnrollment.objects.select_related("candidate", "session__program").get(
            id=enrollment_id
        )
    except TrainingEnrollment.DoesNotExist as exc:
        raise DomainNotFoundError("Enrollment not found.") from exc

    if enrollment.candidate.user_id == actor.id:
        require_permission(actor, TrainingPermissionCode.VIEW_OWN_ENROLLMENTS)
    else:
        require_permission(
            actor,
            TrainingPermissionCode.MANAGE_ENROLLMENTS,
            organization_id=enrollment.session.program.organization_id,
        )
    return enrollment


@transaction.atomic
def enroll_candidate(actor: User, data: Mapping[str, Any]) -> TrainingEnrollment:
    try:
        session = (
            TrainingSession.objects.select_for_update()
            .select_related("program")
            .get(id=data["session_id"])
        )
    except TrainingSession.DoesNotExist as exc:
        raise DomainNotFoundError("Training session not found.") from exc

    if "candidate_id" in data:
        candidate_id = data["candidate_id"]
        require_permission(
            actor,
            TrainingPermissionCode.MANAGE_ENROLLMENTS,
            organization_id=session.program.organization_id,
        )
    else:
        require_permission(actor, TrainingPermissionCode.ENROLL_SELF)
        candidate_id = own_profile(actor).id

    if session.status in ("COMPLETED", "CANCELLED") or session.program.status != "ACTIVE":
        raise DomainValidationError("This training session is not open for enrollment.")

    current_count = TrainingEnrollment.objects.filter(session_id=session.id).count()
    if current_count >= session.capacity:
        raise EnrollmentLimitReachedError()

    try:
        with transaction.atomic():
            return TrainingEnrollment.objects.create(
                session=session,
                candidate_id=candidate_id,
                status=EnrollmentStatus.REGISTERED,
            )
    except IntegrityError as exc:
        if TrainingEnrollment.objects.filter(
            session_id=session.id, candidate_id=candidate_id
        ).exists():
            raise DuplicateEnrollmentError() from exc
        raise DomainNotFoundError("Candidate profile not found.") from exc


def update_progress(
    actor: User, enrollment: TrainingEnrollment, completion_rate: float
) -> TrainingEnrollment:
    require_permission(
        actor,
        TrainingPermissionCode.MANAGE_ENROLLMENTS,
        organization_id=enrollment.session.program.organization_id,
    )
    if enrollment.status in (EnrollmentStatus.COMPLETED, EnrollmentStatus.DROPPED):
        raise DomainValidationError("A completed or dropped enrollment cannot be changed.")
    if enrollment.status == EnrollmentStatus.REGISTERED and completion_rate >= 100.0:
        raise DomainValidationError("Move the enrollment to in progress before completing it.")
    enrollment.completion_rate = completion_rate
    if completion_rate >= 100.0:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = timezone.now()
    elif completion_rate > 0.0 and enrollment.status == EnrollmentStatus.REGISTERED:
        enrollment.status = EnrollmentStatus.IN_PROGRESS
    enrollment.save(update_fields=["completion_rate", "status", "completed_at", "updated_at"])
    return enrollment


def cancel_enrollment(actor: User, enrollment: TrainingEnrollment) -> TrainingEnrollment:
    if enrollment.candidate.user_id == actor.id:
        require_permission(actor, TrainingPermissionCode.ENROLL_SELF)
    else:
        require_permission(
            actor,
            TrainingPermissionCode.MANAGE_ENROLLMENTS,
            organization_id=enrollment.session.program.organization_id,
        )
    if enrollment.status == EnrollmentStatus.COMPLETED:
        raise DomainValidationError("A completed enrollment cannot be dropped.")
    enrollment.status = EnrollmentStatus.DROPPED
    enrollment.save(update_fields=["status", "updated_at"])
    return enrollment
