from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
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
from backend.common.api.query_params import uuid_query_param


class TrainingSkillViewSet(GenericViewSet[TrainingSkill]):
    serializer_class = TrainingSkillReadSerializer
    queryset = TrainingSkill.objects.none()

    @extend_schema(
        parameters=[OpenApiParameter("program_id", UUID, required=True)],
        responses=TrainingSkillReadSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        program_id = uuid_query_param(request, "program_id", required=True)
        queryset = skill_services.list_program_skills(active_request_user(request), program_id)
        page = self.paginate_queryset(queryset)
        serializer = TrainingSkillReadSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        request=TrainingSkillCreateSerializer,
        responses={201: TrainingSkillReadSerializer},
    )
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
