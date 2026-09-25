from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.training.models import DeliveryMode, ProgramLevel, ProgramStatus, TrainingProgram
from backend.apps.training.services.contracts import TrainingPermissionCode
from backend.common.exceptions import DomainNotFoundError


def list_programs(
    actor: User, organization_id: UUID | str | None = None
) -> QuerySet[TrainingProgram]:
    require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    queryset = TrainingProgram.objects.all()
    if organization_id is not None:
        queryset = queryset.filter(organization_id=organization_id)
    return queryset


def get_program(actor: User, program_id: UUID | str) -> TrainingProgram:
    require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    try:
        return TrainingProgram.objects.get(id=program_id)
    except TrainingProgram.DoesNotExist as exc:
        raise DomainNotFoundError("Training program not found.") from exc


def create_program(actor: User, data: Mapping[str, Any]) -> TrainingProgram:
    organization_id = data["organization_id"]
    require_permission(
        actor, TrainingPermissionCode.MANAGE_PROGRAMS, organization_id=organization_id
    )
    return TrainingProgram.objects.create(
        organization_id=organization_id,
        title=data["title"],
        description=data.get("description", ""),
        level=data.get("level", ProgramLevel.BEGINNER),
        delivery_mode=data.get("delivery_mode", DeliveryMode.ONLINE),
        status=data.get("status", ProgramStatus.DRAFT),
        is_paid=data.get("is_paid", False),
        price=data.get("price"),
    )


def update_program(
    actor: User, program: TrainingProgram, data: Mapping[str, Any]
) -> TrainingProgram:
    require_permission(
        actor,
        TrainingPermissionCode.MANAGE_PROGRAMS,
        organization_id=program.organization_id,
    )
    for field in ("title", "description", "level", "delivery_mode", "status", "is_paid", "price"):
        if field in data:
            setattr(program, field, data[field])
    program.save(update_fields=[*data.keys(), "updated_at"])
    return program


def delete_program(actor: User, program: TrainingProgram) -> None:
    require_permission(
        actor,
        TrainingPermissionCode.MANAGE_PROGRAMS,
        organization_id=program.organization_id,
    )
    program.delete()
