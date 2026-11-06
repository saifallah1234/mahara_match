from collections.abc import Mapping
from math import isfinite
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from backend.apps.candidates.services.records import own_profile
from backend.apps.identity.models import RoleCode, User
from backend.apps.identity.services.access import require_permission
from backend.apps.platform.services.records import (
    append_audit,
    notify_role_holders,
    send_notification,
)
from backend.apps.training.models import (
    EnrollmentStatus,
    SessionStatus,
    TrainingEnrollment,
    TrainingSession,
)
from backend.apps.training.services.contracts import TrainingPermissionCode
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


class EnrollmentLimitReachedError(DomainValidationError):
    code = "training_session_full"
    default_message = "Cannot enroll candidate: session capacity reached."


class DuplicateEnrollmentError(DomainValidationError):
    code = "training_duplicate_enrollment"
    default_message = "Candidate is already enrolled in this session."


class RegistrationDeadlinePassedError(DomainValidationError):
    code = "training_registration_closed"
    default_message = "The registration deadline has passed."


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
        return TrainingEnrollment.objects.filter(
            candidate_id=profile.id,
            session__program__organization__deleted_at__isnull=True,
            session__program__organization__verification_status="VERIFIED",
        )
    require_permission(
        actor, TrainingPermissionCode.MANAGE_ENROLLMENTS, organization_id=organization_id
    )
    queryset = TrainingEnrollment.objects.filter(
        session__program__organization_id=organization_id,
        session__program__organization__deleted_at__isnull=True,
    )
    return queryset.filter(candidate_id=candidate_id) if candidate_id else queryset


def get_enrollment(actor: User, enrollment_id: UUID | str) -> TrainingEnrollment:
    try:
        enrollment = TrainingEnrollment.objects.select_related(
            "candidate", "session__program__organization"
        ).get(id=enrollment_id, session__program__organization__deleted_at__isnull=True)
    except TrainingEnrollment.DoesNotExist as exc:
        raise DomainNotFoundError("Enrollment not found.") from exc

    if enrollment.candidate.user_id == actor.id:
        if enrollment.session.program.organization.verification_status != "VERIFIED":
            raise DomainNotFoundError("Enrollment not found.")
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
            TrainingSession.objects.select_for_update(of=("self",))
            .select_related("program__organization")
            .get(id=data["session_id"], program__organization__deleted_at__isnull=True)
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

    if (
        session.status in ("COMPLETED", "CANCELLED")
        or session.program.status != "ACTIVE"
        or session.program.organization.verification_status != "VERIFIED"
    ):
        raise DomainValidationError("This training session is not open for enrollment.")

    if session.registration_deadline is not None and timezone.now() > session.registration_deadline:
        raise RegistrationDeadlinePassedError()
    if TrainingEnrollment.objects.filter(session_id=session.id, candidate_id=candidate_id).exists():
        raise DuplicateEnrollmentError()
    current_count = (
        TrainingEnrollment.objects.filter(session_id=session.id)
        .exclude(status=EnrollmentStatus.DROPPED)
        .count()
    )
    if current_count >= session.capacity:
        raise EnrollmentLimitReachedError()

    try:
        with transaction.atomic():
            enrollment = TrainingEnrollment.objects.create(
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
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="training.enrollment.enroll",
        entity_type="training_enrollment",
        entity_id=enrollment.id,
        after={"status": enrollment.status, "session_id": str(session.id)},
    )
    notify_role_holders(
        actor,
        session.program.organization_id,
        RoleCode.TRAINING_MANAGER,
        type="training.enrollment.created",
        title="Nouvelle inscription",
        body=f"Une inscription a été enregistrée pour « {session.program.title} ».",
        payload_json={"enrollment_id": str(enrollment.id), "session_id": str(session.id)},
    )
    return enrollment


def _lock_enrollment(enrollment: TrainingEnrollment) -> TrainingEnrollment:
    # Every lifecycle writer locks the session first, then the enrollment.
    TrainingSession.objects.select_for_update(of=("self",)).get(pk=enrollment.session_id)
    return (
        TrainingEnrollment.objects.select_for_update(of=("self",))
        .select_related("session__program__organization", "candidate")
        .get(pk=enrollment.pk)
    )


@transaction.atomic
def update_progress(
    actor: User, enrollment: TrainingEnrollment, completion_rate: float
) -> TrainingEnrollment:
    enrollment = _lock_enrollment(enrollment)
    require_permission(
        actor,
        TrainingPermissionCode.MANAGE_ENROLLMENTS,
        organization_id=enrollment.session.program.organization_id,
    )
    if enrollment.session.program.organization.deleted_at is not None:
        raise DomainNotFoundError("Enrollment not found.")
    if enrollment.session.status == SessionStatus.CANCELLED:
        raise DomainValidationError("Progress cannot change after session cancellation.")
    if not isfinite(completion_rate) or not 0.0 <= completion_rate <= 100.0:
        raise DomainValidationError(details={"completion_rate": ["Must be between 0 and 100."]})
    if enrollment.status in (EnrollmentStatus.COMPLETED, EnrollmentStatus.DROPPED):
        raise DomainValidationError("A completed or dropped enrollment cannot be changed.")
    if enrollment.status == EnrollmentStatus.REGISTERED and completion_rate >= 100.0:
        raise DomainValidationError("Move the enrollment to in progress before completing it.")
    previous_status = enrollment.status
    enrollment.completion_rate = completion_rate
    if completion_rate >= 100.0:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = timezone.now()
    elif completion_rate > 0.0 and enrollment.status == EnrollmentStatus.REGISTERED:
        enrollment.status = EnrollmentStatus.IN_PROGRESS
    enrollment.save(update_fields=["completion_rate", "status", "completed_at", "updated_at"])
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="training.enrollment.progress",
        entity_type="training_enrollment",
        entity_id=enrollment.id,
        before={"status": previous_status},
        after={"status": enrollment.status, "completion_rate": completion_rate},
    )
    if enrollment.status != previous_status:
        _notify_candidate_status(enrollment)
    return enrollment


def _notify_candidate_status(enrollment: TrainingEnrollment) -> None:
    send_notification(
        enrollment.candidate.user,
        type="training.enrollment.status_changed",
        title="Inscription mise à jour",
        body=f"Le statut de votre inscription à « {enrollment.session.program.title} » a changé.",
        payload_json={"enrollment_id": str(enrollment.id), "status": enrollment.status},
    )


@transaction.atomic
def cancel_enrollment(actor: User, enrollment: TrainingEnrollment) -> TrainingEnrollment:
    enrollment = _lock_enrollment(enrollment)
    if enrollment.candidate.user_id == actor.id:
        require_permission(actor, TrainingPermissionCode.ENROLL_SELF)
    else:
        require_permission(
            actor,
            TrainingPermissionCode.MANAGE_ENROLLMENTS,
            organization_id=enrollment.session.program.organization_id,
        )
    if enrollment.session.program.organization.deleted_at is not None:
        raise DomainNotFoundError("Enrollment not found.")
    if enrollment.status == EnrollmentStatus.COMPLETED:
        raise DomainValidationError("A completed enrollment cannot be dropped.")
    if enrollment.status == EnrollmentStatus.DROPPED:
        return enrollment
    previous_status = enrollment.status
    enrollment.status = EnrollmentStatus.DROPPED
    enrollment.save(update_fields=["status", "updated_at"])
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="training.enrollment.cancel",
        entity_type="training_enrollment",
        entity_id=enrollment.id,
        before={"status": previous_status},
        after={"status": EnrollmentStatus.DROPPED},
    )
    if enrollment.candidate.user_id == actor.id:
        notify_role_holders(
            actor,
            enrollment.session.program.organization_id,
            RoleCode.TRAINING_MANAGER,
            type="training.enrollment.cancelled",
            title="Inscription annulée",
            body=f"Un candidat a annulé son inscription à « {enrollment.session.program.title} ».",
            payload_json={
                "enrollment_id": str(enrollment.id),
                "session_id": str(enrollment.session_id),
            },
        )
    else:
        _notify_candidate_status(enrollment)
    return enrollment
