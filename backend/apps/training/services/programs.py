from uuid import UUID

from backend.apps.training.models import TrainingProgram
from backend.apps.training.services.contracts import ProgramDTO


class ProgramService:
    @staticmethod
    def create_program(dto: ProgramDTO) -> TrainingProgram:
        program = TrainingProgram.objects.create(
            organization_id=dto.organization_id,
            title=dto.title,
            description=dto.description,
            level=dto.level,
            delivery_mode=dto.delivery_mode,
            status=dto.status,
            is_paid=dto.is_paid,
            price=dto.price,
        )
        return program

    @staticmethod
    def get_by_id(program_id: UUID) -> TrainingProgram | None:
        return TrainingProgram.objects.filter(id=program_id).first()

    @staticmethod
    def list_organization_programs(organization_id: UUID) -> list[TrainingProgram]:
        return list(TrainingProgram.objects.filter(organization_id=organization_id))
