from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import IsActiveAuthenticated, active_request_user
from backend.apps.recruitment.api.interviews_serializers import (
    InterviewReadSerializer,
    InterviewScheduleSerializer,
    InterviewTransitionSerializer,
)
from backend.apps.recruitment.api.query_params import optional_uuid_param
from backend.apps.recruitment.models import Interview
from backend.apps.recruitment.services import interviews as interview_services
from backend.apps.recruitment.services.interview_lifecycle import (
    finish_interview,
    schedule_interview,
)


class InterviewViewSet(GenericViewSet[Interview]):
    serializer_class = InterviewReadSerializer
    queryset = Interview.objects.none()
    permission_classes = (IsActiveAuthenticated,)

    @extend_schema(
        parameters=[OpenApiParameter("application_id", UUID, required=False)],
        responses=InterviewReadSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        queryset = interview_services.list_interviews(
            active_request_user(request),
            application_id=optional_uuid_param(request, "application_id"),
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            InterviewReadSerializer(page, many=True, context={"request": request}).data
        )

    def retrieve(self, request: Request, pk: UUID) -> Response:
        interview = interview_services.get_interview(active_request_user(request), pk)
        return Response(InterviewReadSerializer(interview, context={"request": request}).data)

    @extend_schema(request=InterviewScheduleSerializer, responses={201: InterviewReadSerializer})
    def create(self, request: Request) -> Response:
        serializer = InterviewScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interview = schedule_interview(active_request_user(request), serializer.validated_data)
        return Response(
            InterviewReadSerializer(interview, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=InterviewTransitionSerializer, responses=InterviewReadSerializer)
    @action(detail=True, methods=["post"])
    def transition(self, request: Request, pk: UUID) -> Response:
        serializer = InterviewTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interview = finish_interview(
            active_request_user(request),
            pk,
            serializer.validated_data["status"],
            serializer.validated_data.get("feedback", ""),
        )
        return Response(InterviewReadSerializer(interview, context={"request": request}).data)
