from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.training.models import SessionStatus, TrainingProgram, TrainingSession
from backend.apps.training.services.contracts import TrainingPermissionCode
from backend.common.exceptions import DomainNotFoundError


def list_program_sessions(actor: User, program_id: UUID | str) -> QuerySet[TrainingSession]:
    require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    return TrainingSession.objects.filter(program_id=program_id)


def get_session(actor: User, session_id: UUID | str) -> TrainingSession:
    require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    try:
        return TrainingSession.objects.select_related("program").get(id=session_id)
    except TrainingSession.DoesNotExist as exc:
        raise DomainNotFoundError("Training session not found.") from exc


def create_session(actor: User, data: Mapping[str, Any]) -> TrainingSession:
    try:
        program = TrainingProgram.objects.get(id=data["program_id"])
    except TrainingProgram.DoesNotExist as exc:
        raise DomainNotFoundError("Training program not found.") from exc

    require_permission(
        actor, TrainingPermissionCode.MANAGE_SESSIONS, organization_id=program.organization_id
    )
    return TrainingSession.objects.create(
        program=program,
        start_date=data["start_date"],
        end_date=data["end_date"],
        capacity=data["capacity"],
        location_or_url=data["location_or_url"],
        registration_deadline=data["registration_deadline"],
        status=data.get("status", SessionStatus.PLANNED),
    )


def update_session(
    actor: User, session: TrainingSession, data: Mapping[str, Any]
) -> TrainingSession:
    require_permission(
        actor,
        TrainingPermissionCode.MANAGE_SESSIONS,
        organization_id=session.program.organization_id,
    )
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
    return session


def delete_session(actor: User, session: TrainingSession) -> None:
    require_permission(
        actor,
        TrainingPermissionCode.MANAGE_SESSIONS,
        organization_id=session.program.organization_id,
    )
    session.delete()
