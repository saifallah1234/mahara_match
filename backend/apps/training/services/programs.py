from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import IntegrityError
from django.db.models import QuerySet

from backend.apps.identity.models import Organization, OrganizationType, User
from backend.apps.identity.models.organizations import VerificationStatus
from backend.apps.identity.services.access import require_permission
from backend.apps.training.models import DeliveryMode, ProgramLevel, ProgramStatus, TrainingProgram
from backend.apps.training.services.contracts import TrainingPermissionCode
from backend.common.exceptions import (
    DomainNotFoundError,
    DomainPermissionError,
    DomainValidationError,
)


def list_programs(
    actor: User, organization_id: UUID | str | None = None
) -> QuerySet[TrainingProgram]:
    if organization_id is None:
        require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
        return TrainingProgram.objects.filter(
            status=ProgramStatus.ACTIVE,
            organization__deleted_at__isnull=True,
            organization__verification_status=VerificationStatus.VERIFIED,
        )
    require_permission(actor, TrainingPermissionCode.VIEW_CATALOG, organization_id=organization_id)
    queryset = TrainingProgram.objects.filter(
        organization_id=organization_id,
        organization__deleted_at__isnull=True,
    )
    try:
        require_permission(
            actor, TrainingPermissionCode.MANAGE_PROGRAMS, organization_id=organization_id
        )
    except DomainPermissionError:
        queryset = queryset.filter(
            status=ProgramStatus.ACTIVE,
            organization__verification_status=VerificationStatus.VERIFIED,
        )
    return queryset


def get_program(actor: User, program_id: UUID | str) -> TrainingProgram:
    try:
        program = TrainingProgram.objects.select_related("organization").get(
            id=program_id, organization__deleted_at__isnull=True
        )
    except TrainingProgram.DoesNotExist as exc:
        raise DomainNotFoundError("Training program not found.") from exc
    if (
        program.status != ProgramStatus.ACTIVE
        or program.organization.verification_status != VerificationStatus.VERIFIED
    ):
        require_permission(
            actor,
            TrainingPermissionCode.MANAGE_PROGRAMS,
            organization_id=program.organization_id,
        )
    else:
        require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    return program


def create_program(actor: User, data: Mapping[str, Any]) -> TrainingProgram:
    _validate_price(data.get("is_free", True), data.get("price", 0))
    organization_id = data["organization_id"]
    require_permission(
        actor, TrainingPermissionCode.MANAGE_PROGRAMS, organization_id=organization_id
    )
    try:
        organization = Organization.objects.get(
            id=organization_id,
            type=OrganizationType.TRAINING_PROVIDER,
            deleted_at__isnull=True,
        )
        return TrainingProgram.objects.create(
            organization=organization,
            title=data["title"],
            description=data.get("description", ""),
            level=data.get("level", ProgramLevel.BEGINNER),
            delivery_mode=data.get("delivery_mode", DeliveryMode.ONLINE),
            status=data.get("status", ProgramStatus.DRAFT),
            is_free=data.get("is_free", True),
            price=data.get("price", 0),
        )
    except (IntegrityError, Organization.DoesNotExist) as exc:
        raise DomainValidationError(
            details={"organization_id": ["Organization not found or invalid program data."]}
        ) from exc


def update_program(
    actor: User, program: TrainingProgram, data: Mapping[str, Any]
) -> TrainingProgram:
    require_permission(
        actor,
        TrainingPermissionCode.MANAGE_PROGRAMS,
        organization_id=program.organization_id,
    )
    _validate_price(data.get("is_free", program.is_free), data.get("price", program.price))
    for field in ("title", "description", "level", "delivery_mode", "status", "is_free", "price"):
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
    program.status = ProgramStatus.ARCHIVED
    program.save(update_fields=["status", "updated_at"])


def _validate_price(is_free: bool, price: Any) -> None:
    if (is_free and price != 0) or (not is_free and price <= 0):
        raise DomainValidationError(
            details={"price": ["Free programs cost 0 TND; paid programs cost more than 0 TND."]}
        )
