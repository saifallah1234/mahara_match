from uuid import UUID

from backend.apps.training.models import TrainingSession


class SessionService:
    @staticmethod
    def create_session(
        program_id: UUID,
        start_date,
        end_date,
        capacity: int,
        location_or_url: str,
        registration_deadline,
        status: str = "PLANNED",
    ) -> TrainingSession:
        return TrainingSession.objects.create(
            program_id=program_id,
            start_date=start_date,
            end_date=end_date,
            capacity=capacity,
            location_or_url=location_or_url,
            registration_deadline=registration_deadline,
            status=status,
        )

    @staticmethod
    def get_by_id(session_id: UUID) -> TrainingSession | None:
        return TrainingSession.objects.filter(id=session_id).first()

    @staticmethod
    def list_program_sessions(program_id: UUID) -> list[TrainingSession]:
        return list(TrainingSession.objects.filter(program_id=program_id))
