from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import IntegrityError
from django.db.models import QuerySet

from backend.apps.candidates.services.records import own_profile
from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.training.models import TrainingProgram, TrainingRecommendation
from backend.apps.training.services.contracts import TrainingPermissionCode
from backend.common.exceptions import DomainNotFoundError, DomainValidationError


def list_recommendations(
    actor: User,
    candidate_id: UUID | str | None = None,
    organization_id: UUID | str | None = None,
) -> QuerySet[TrainingRecommendation]:
    if organization_id is None:
        profile = own_profile(actor)
        require_permission(actor, TrainingPermissionCode.VIEW_OWN_RECOMMENDATIONS)
        if candidate_id is not None and str(candidate_id) != str(profile.id):
            return TrainingRecommendation.objects.none()
        return TrainingRecommendation.objects.filter(
            candidate_id=profile.id,
            program__organization__deleted_at__isnull=True,
            program__organization__verification_status="VERIFIED",
        )
    require_permission(
        actor, TrainingPermissionCode.MANAGE_RECOMMENDATIONS, organization_id=organization_id
    )
    queryset = TrainingRecommendation.objects.filter(
        program__organization_id=organization_id,
        program__organization__deleted_at__isnull=True,
    )
    return queryset.filter(candidate_id=candidate_id) if candidate_id else queryset


def get_recommendation(actor: User, recommendation_id: UUID | str) -> TrainingRecommendation:
    try:
        recommendation = TrainingRecommendation.objects.select_related(
            "candidate", "program__organization"
        ).get(id=recommendation_id, program__organization__deleted_at__isnull=True)
    except TrainingRecommendation.DoesNotExist as exc:
        raise DomainNotFoundError("Recommendation not found.") from exc

    if recommendation.candidate.user_id == actor.id:
        if recommendation.program.organization.verification_status != "VERIFIED":
            raise DomainNotFoundError("Recommendation not found.")
        require_permission(actor, TrainingPermissionCode.VIEW_OWN_RECOMMENDATIONS)
    else:
        require_permission(
            actor,
            TrainingPermissionCode.MANAGE_RECOMMENDATIONS,
            organization_id=recommendation.program.organization_id,
        )
    return recommendation


def record_recommendation(actor: User, data: Mapping[str, Any]) -> TrainingRecommendation:
    try:
        program = TrainingProgram.objects.get(
            id=data["program_id"], organization__deleted_at__isnull=True
        )
    except TrainingProgram.DoesNotExist as exc:
        raise DomainNotFoundError("Training program not found.") from exc
    require_permission(
        actor,
        TrainingPermissionCode.MANAGE_RECOMMENDATIONS,
        organization_id=program.organization_id,
    )
    if not 0 <= data["score"] <= 100:
        raise DomainValidationError(details={"score": ["Score must be between 0 and 100."]})
    try:
        return TrainingRecommendation.objects.create(
            candidate_id=data["candidate_id"],
            program=program,
            reason_json=data.get("reason_json", {}),
            score=data["score"],
            model_version=data["model_version"],
        )
    except IntegrityError as exc:
        raise DomainValidationError(
            details={"candidate_id": ["Candidate profile not found."]}
        ) from exc
