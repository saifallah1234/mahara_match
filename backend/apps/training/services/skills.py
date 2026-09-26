from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import IntegrityError
from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.training.models import (
    ProgramStatus,
    TrainingProgram,
    TrainingSkill,
    TrainingSkillPurpose,
)
from backend.apps.training.services.contracts import TrainingPermissionCode
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


def list_program_skills(actor: User, program_id: UUID | str) -> QuerySet[TrainingSkill]:
    try:
        program = TrainingProgram.objects.get(id=program_id)
    except TrainingProgram.DoesNotExist as exc:
        raise DomainNotFoundError("Training program not found.") from exc
    if program.status == ProgramStatus.ACTIVE:
        require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    else:
        require_permission(
            actor, TrainingPermissionCode.MANAGE_SKILLS, organization_id=program.organization_id
        )
    return TrainingSkill.objects.filter(program_id=program_id)


def get_skill(actor: User, skill_id: UUID | str) -> TrainingSkill:
    require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    try:
        skill = TrainingSkill.objects.select_related("program").get(id=skill_id)
    except TrainingSkill.DoesNotExist as exc:
        raise DomainNotFoundError("Training skill not found.") from exc
    if skill.program.status == ProgramStatus.ACTIVE:
        require_permission(actor, TrainingPermissionCode.VIEW_CATALOG)
    else:
        require_permission(
            actor,
            TrainingPermissionCode.MANAGE_SKILLS,
            organization_id=skill.program.organization_id,
        )
    return skill


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
            purpose=data.get("purpose", TrainingSkillPurpose.TAUGHT),
        )
    except IntegrityError as exc:
        duplicate = TrainingSkill.objects.filter(
            program=program, skill_id=data["skill_id"], purpose=data.get("purpose", "TAUGHT")
        ).exists()
        message = (
            "This skill and purpose are already attached to the program."
            if duplicate
            else "Skill not found."
        )
        raise DomainValidationError(details={"skill_id": [message]}) from exc


def remove_skill(actor: User, skill: TrainingSkill) -> None:
    require_permission(
        actor,
        TrainingPermissionCode.MANAGE_SKILLS,
        organization_id=skill.program.organization_id,
    )
    skill.delete()
