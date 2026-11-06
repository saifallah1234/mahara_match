from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.platform.services.records import append_audit
from backend.apps.training.models import (
    EnrollmentStatus,
    ProgramStatus,
    SessionStatus,
    TrainingEnrollment,
    TrainingProgram,
    TrainingSession,
)
from backend.apps.training.services.contracts import TrainingPermissionCode
from backend.common.exceptions import (
    DomainNotFoundError,
    DomainPermissionError,
    DomainValidationError,
)


def list_program_sessions(actor: User, program_id: UUID) -> QuerySet[TrainingSession]:
    require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    try:
        organization_id = TrainingProgram.objects.values_list("organization_id", flat=True).get(
            id=program_id, organization__deleted_at__isnull=True
        )
        require_permission(
            actor,
            TrainingPermissionCode.MANAGE_SESSIONS,
            organization_id=organization_id,
        )
    except (DomainPermissionError, TrainingProgram.DoesNotExist):
        return _catalogue_sessions().filter(program_id=program_id)
    return TrainingSession.objects.filter(program_id=program_id)


def list_catalogue_sessions(actor: User) -> QuerySet[TrainingSession]:
    require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    return _catalogue_sessions()


def _catalogue_sessions() -> QuerySet[TrainingSession]:
    return TrainingSession.objects.filter(
        program__status=ProgramStatus.ACTIVE,
        program__organization__deleted_at__isnull=True,
        program__organization__verification_status="VERIFIED",
        status__in=(SessionStatus.PLANNED, SessionStatus.ONGOING),
    )


def get_session(actor: User, session_id: UUID | str) -> TrainingSession:
    require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    try:
        session = TrainingSession.objects.select_related("program__organization").get(
            id=session_id, program__organization__deleted_at__isnull=True
        )
    except TrainingSession.DoesNotExist as exc:
        raise DomainNotFoundError("Training session not found.") from exc
    if (
        session.program.status != ProgramStatus.ACTIVE
        or session.program.organization.verification_status != "VERIFIED"
        or session.status in (SessionStatus.CANCELLED, SessionStatus.COMPLETED)
    ):
        require_permission(
            actor,
            TrainingPermissionCode.MANAGE_SESSIONS,
            organization_id=session.program.organization_id,
        )
    else:
        require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    return session


def create_session(actor: User, data: Mapping[str, Any]) -> TrainingSession:
    try:
        program = TrainingProgram.objects.get(
            id=data["program_id"], organization__deleted_at__isnull=True
        )
    except TrainingProgram.DoesNotExist as exc:
        raise DomainNotFoundError("Training program not found.") from exc

    require_permission(
        actor, TrainingPermissionCode.MANAGE_SESSIONS, organization_id=program.organization_id
    )
    _validate_dates(data["start_date"], data["end_date"], data["registration_deadline"])
    return TrainingSession.objects.create(
        program=program,
        start_date=data["start_date"],
        end_date=data["end_date"],
        capacity=data["capacity"],
        location_or_url=data["location_or_url"],
        registration_deadline=data["registration_deadline"],
        status=data.get("status", SessionStatus.PLANNED),
    )


@transaction.atomic
def update_session(
    actor: User, session: TrainingSession, data: Mapping[str, Any]
) -> TrainingSession:
    try:
        session = (
            TrainingSession.objects.select_for_update(of=("self",))
            .select_related("program")
            .get(pk=session.pk, program__organization__deleted_at__isnull=True)
        )
    except TrainingSession.DoesNotExist as exc:
        raise DomainNotFoundError("Training session not found.") from exc
    require_permission(
        actor,
        TrainingPermissionCode.MANAGE_SESSIONS,
        organization_id=session.program.organization_id,
    )
    if (
        session.status in (SessionStatus.COMPLETED, SessionStatus.CANCELLED)
        and data.get("status", session.status) != session.status
    ):
        raise DomainValidationError("A completed or cancelled session cannot change status.")
    if (
        "capacity" in data
        and data["capacity"]
        < TrainingEnrollment.objects.filter(session=session)
        .exclude(status=EnrollmentStatus.DROPPED)
        .count()
    ):
        raise DomainValidationError(details={"capacity": ["Cannot be below occupied capacity."]})
    _validate_dates(
        data.get("start_date", session.start_date),
        data.get("end_date", session.end_date),
        data.get("registration_deadline", session.registration_deadline),
    )
    previous_status = session.status
    for field in (
        "start_date",
        "end_date",
        "capacity",
        "location_or_url",
        "registration_deadline",
        "status",
    ):
        if field in data:
            setattr(session, field, data[field])
    session.save(update_fields=[*data.keys(), "updated_at"])
    append_audit(
        actor_type="USER",
        actor_user=actor,
        action="training.session.update",
        entity_type="training_session",
        entity_id=session.id,
        before={"status": previous_status},
        after={"status": session.status, "changed_fields": list(data)},
    )
    return session


def delete_session(actor: User, session: TrainingSession) -> None:
    update_session(actor, session, {"status": SessionStatus.CANCELLED})


def _validate_dates(start_date: Any, end_date: Any, deadline: Any) -> None:
    errors: dict[str, list[str]] = {}
    if end_date <= start_date:
        errors["end_date"] = ["Must be after the start date."]
    if deadline > start_date:
        errors["registration_deadline"] = ["Must be on or before the start date."]
    if errors:
        raise DomainValidationError(details=errors)
