from uuid import UUID

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.training.api.skills_serializers import (
    TrainingSkillCreateSerializer,
    TrainingSkillReadSerializer,
)
from backend.apps.training.models import TrainingSkill
from backend.apps.training.services import skills as skill_services
from backend.common.exceptions import DomainValidationError


class TrainingSkillViewSet(GenericViewSet[TrainingSkill]):
    serializer_class = TrainingSkillReadSerializer
    queryset = TrainingSkill.objects.none()

    def list(self, request: Request) -> Response:
        program_id = request.query_params.get("program_id")
        if not program_id:
            raise DomainValidationError(
                details={"program_id": ["This query parameter is required."]}
            )
        queryset = skill_services.list_program_skills(active_request_user(request), program_id)
        page = self.paginate_queryset(queryset)
        serializer = TrainingSkillReadSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def create(self, request: Request) -> Response:
        serializer = TrainingSkillCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        skill = skill_services.add_skill(active_request_user(request), serializer.validated_data)
        return Response(TrainingSkillReadSerializer(skill).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        skill = skill_services.get_skill(active_request_user(request), pk)
        return Response(TrainingSkillReadSerializer(skill).data)

    def destroy(self, request: Request, pk: UUID) -> Response:
        actor = active_request_user(request)
        skill = skill_services.get_skill(actor, pk)
        skill_services.remove_skill(actor, skill)
        return Response(status=status.HTTP_204_NO_CONTENT)
