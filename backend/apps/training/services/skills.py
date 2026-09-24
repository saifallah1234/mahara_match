from uuid import UUID

from backend.apps.training.models import TrainingSkill


class SkillService:
    @staticmethod
    def add_skill_to_program(program_id: UUID, skill_id: UUID, target_level: str) -> TrainingSkill:
        return TrainingSkill.objects.create(
            program_id=program_id,
            skill_id=skill_id,
            target_level=target_level,
        )

    @staticmethod
    def list_program_skills(program_id: UUID) -> list[TrainingSkill]:
        return list(TrainingSkill.objects.filter(program_id=program_id))

    @staticmethod
    def remove_skill_from_program(program_id: UUID, skill_id: UUID) -> bool:
        deleted, _ = TrainingSkill.objects.filter(program_id=program_id, skill_id=skill_id).delete()
        return deleted > 0
