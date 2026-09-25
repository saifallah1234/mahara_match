from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import IntegrityError
from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.training.models import TrainingProgram, TrainingSkill
from backend.apps.training.services.contracts import TrainingPermissionCode
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


def list_program_skills(actor: User, program_id: UUID | str) -> QuerySet[TrainingSkill]:
    require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    return TrainingSkill.objects.filter(program_id=program_id)


def get_skill(actor: User, skill_id: UUID | str) -> TrainingSkill:
    require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    try:
        return TrainingSkill.objects.select_related("program").get(id=skill_id)
    except TrainingSkill.DoesNotExist as exc:
        raise DomainNotFoundError("Training skill not found.") from exc


def add_skill(actor: User, data: Mapping[str, Any]) -> TrainingSkill:
    try:
        program = TrainingProgram.objects.get(id=data["program_id"])
    except TrainingProgram.DoesNotExist as exc:
        raise DomainNotFoundError("Training program not found.") from exc

    require_permission(
        actor, TrainingPermissionCode.MANAGE_SKILLS, organization_id=program.organization_id
    )
    try:
        return TrainingSkill.objects.create(
            program=program,
            skill_id=data["skill_id"],
            target_level=data["target_level"],
        )
    except IntegrityError as exc:
        raise DomainValidationError(
            details={"skill_id": ["This skill is already attached to the program."]}
        ) from exc


def remove_skill(actor: User, skill: TrainingSkill) -> None:
    require_permission(
        actor,
        TrainingPermissionCode.MANAGE_SKILLS,
        organization_id=skill.program.organization_id,
    )
    skill.delete()
