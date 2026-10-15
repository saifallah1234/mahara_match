from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.training.api.recommendations_serializers import (
    TrainingRecommendationCreateSerializer,
    TrainingRecommendationReadSerializer,
)
from backend.apps.training.models import TrainingRecommendation
from backend.apps.training.services import recommendations as recommendation_services
from backend.common.api.query_params import uuid_query_param


class TrainingRecommendationViewSet(GenericViewSet[TrainingRecommendation]):
    serializer_class = TrainingRecommendationReadSerializer
    queryset = TrainingRecommendation.objects.none()

    @extend_schema(
        parameters=[
            OpenApiParameter("candidate_id", UUID, required=False),
            OpenApiParameter("organization_id", UUID, required=False),
        ],
        responses=TrainingRecommendationReadSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        queryset = recommendation_services.list_recommendations(
            active_request_user(request),
            candidate_id=uuid_query_param(request, "candidate_id"),
            organization_id=uuid_query_param(request, "organization_id"),
        )
        page = self.paginate_queryset(queryset)
        serializer = TrainingRecommendationReadSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        request=TrainingRecommendationCreateSerializer,
        responses={201: TrainingRecommendationReadSerializer},
    )
    def create(self, request: Request) -> Response:
        serializer = TrainingRecommendationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recommendation = recommendation_services.record_recommendation(
            active_request_user(request), serializer.validated_data
        )
        return Response(
            TrainingRecommendationReadSerializer(recommendation).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request: Request, pk: UUID) -> Response:
        recommendation = recommendation_services.get_recommendation(
            active_request_user(request), pk
        )
        return Response(TrainingRecommendationReadSerializer(recommendation).data)
