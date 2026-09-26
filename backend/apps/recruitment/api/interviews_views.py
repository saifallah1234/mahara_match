from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import IsActiveAuthenticated, active_request_user
from backend.apps.recruitment.api.interviews_serializers import InterviewReadSerializer
from backend.apps.recruitment.api.query_params import optional_uuid_param
from backend.apps.recruitment.models import Interview
from backend.apps.recruitment.services import interviews as interview_services


class InterviewViewSet(GenericViewSet[Interview]):
    serializer_class = InterviewReadSerializer
    queryset = Interview.objects.none()
    permission_classes = (IsActiveAuthenticated,)

    @extend_schema(responses=InterviewReadSerializer(many=True))
    def list(self, request: Request) -> Response:
        queryset = interview_services.list_interviews(
            active_request_user(request),
            application_id=optional_uuid_param(request, "application_id"),
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(InterviewReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        interview = interview_services.get_interview(active_request_user(request), pk)
        return Response(InterviewReadSerializer(interview).data)
