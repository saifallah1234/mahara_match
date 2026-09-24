from uuid import UUID

from backend.apps.training.models import TrainingRecommendation
from backend.apps.training.services.contracts import RecommendationDTO


class RecommendationService:
    @staticmethod
    def record_recommendation(dto: RecommendationDTO) -> TrainingRecommendation:
        return TrainingRecommendation.objects.create(
            candidate_id=dto.candidate_id,
            program_id=dto.program_id,
            reason_json=dto.reason_json,
            score=dto.score,
            model_version=dto.model_version,
        )

    @staticmethod
    def get_candidate_recommendations(candidate_id: UUID) -> list[TrainingRecommendation]:
        return list(TrainingRecommendation.objects.filter(candidate_id=candidate_id))
