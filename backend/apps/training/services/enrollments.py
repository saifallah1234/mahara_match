from uuid import UUID

from django.utils import timezone

from backend.apps.training.models import EnrollmentStatus, TrainingEnrollment, TrainingSession
from backend.apps.training.services.contracts import EnrollmentDTO
from backend.common.exceptions.domain import DomainNotFoundError, DomainValidationError


class EnrollmentLimitReachedError(DomainValidationError):
    """Raised when a candidate tries to enroll in a full session."""

    code = "training_session_full"
    default_message = "Cannot enroll candidate: session maximum capacity reached."


class DuplicateEnrollmentError(DomainValidationError):
    """Raised when a candidate is already registered for a session."""

    code = "training_duplicate_enrollment"
    default_message = "Candidate is already enrolled in this session."


class EnrollmentService:
    @staticmethod
    def enroll_candidate(dto: EnrollmentDTO) -> TrainingEnrollment:
        session = TrainingSession.objects.filter(id=dto.session_id).first()
        if not session:
            raise DomainNotFoundError(message="Session not found.")

        # Check capacity rule
        current_count = TrainingEnrollment.objects.filter(session_id=dto.session_id).count()
        if current_count >= session.capacity:
            raise EnrollmentLimitReachedError()

        # Check duplicate enrollment constraint
        if TrainingEnrollment.objects.filter(
            session_id=dto.session_id, candidate_id=dto.candidate_id
        ).exists():
            raise DuplicateEnrollmentError()

        return TrainingEnrollment.objects.create(
            session_id=dto.session_id,
            candidate_id=dto.candidate_id,
            status=dto.status,
        )

    @staticmethod
    def update_progress(enrollment_id: UUID, completion_rate: float) -> TrainingEnrollment:
        enrollment = TrainingEnrollment.objects.filter(id=enrollment_id).first()
        if not enrollment:
            raise DomainNotFoundError(message="Enrollment record not found.")

        enrollment.completion_rate = completion_rate

        if completion_rate >= 100.0:
            enrollment.status = EnrollmentStatus.COMPLETED
            enrollment.completed_at = timezone.now()
        elif completion_rate > 0.0 and enrollment.status == EnrollmentStatus.REGISTERED:
            enrollment.status = EnrollmentStatus.IN_PROGRESS

        enrollment.save()
        return enrollment

    @staticmethod
    def list_candidate_enrollments(candidate_id: UUID) -> list[TrainingEnrollment]:
        return list(TrainingEnrollment.objects.filter(candidate_id=candidate_id))
