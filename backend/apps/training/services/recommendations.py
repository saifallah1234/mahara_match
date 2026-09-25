from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.training.models import TrainingRecommendation
from backend.apps.training.services.contracts import TrainingPermissionCode
from backend.common.exceptions import DomainNotFoundError


def list_recommendations(
    actor: User, candidate_id: UUID | str | None = None
) -> QuerySet[TrainingRecommendation]:
    if candidate_id is None or str(candidate_id) == str(actor.id):
        require_permission(actor, TrainingPermissionCode.VIEW_OWN_RECOMMENDATIONS)
        return TrainingRecommendation.objects.filter(candidate_id=candidate_id or actor.id)
    require_permission(actor, TrainingPermissionCode.MANAGE_RECOMMENDATIONS)
    return TrainingRecommendation.objects.filter(candidate_id=candidate_id)


def get_recommendation(actor: User, recommendation_id: UUID | str) -> TrainingRecommendation:
    try:
        recommendation = TrainingRecommendation.objects.get(id=recommendation_id)
    except TrainingRecommendation.DoesNotExist as exc:
        raise DomainNotFoundError("Recommendation not found.") from exc

    if str(recommendation.candidate_id) == str(actor.id):
        require_permission(actor, TrainingPermissionCode.VIEW_OWN_RECOMMENDATIONS)
    else:
        require_permission(actor, TrainingPermissionCode.MANAGE_RECOMMENDATIONS)
    return recommendation


def record_recommendation(actor: User, data: Mapping[str, Any]) -> TrainingRecommendation:
    require_permission(actor, TrainingPermissionCode.MANAGE_RECOMMENDATIONS)
    return TrainingRecommendation.objects.create(
        candidate_id=data["candidate_id"],
        program_id=data["program_id"],
        reason_json=data.get("reason_json", {}),
        score=data["score"],
        model_version=data["model_version"],
    )
