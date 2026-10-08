from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.recruitment.api.filters import JobOfferFilters
from backend.apps.recruitment.api.job_offers_permissions import IsActiveAuthenticated
from backend.apps.recruitment.api.job_offers_serializers import (
    JobOfferCreateSerializer,
    JobOfferReadSerializer,
    JobOfferTransitionSerializer,
    JobOfferUpdateSerializer,
)
from backend.apps.recruitment.models import JobOffer
from backend.apps.recruitment.services import job_offers as offer_services
from backend.apps.recruitment.services.offer_lifecycle import transition_offer


class JobOfferViewSet(GenericViewSet[JobOffer]):
    serializer_class = JobOfferReadSerializer
    queryset = JobOffer.objects.none()
    permission_classes = (IsActiveAuthenticated,)

    @extend_schema(parameters=[JobOfferFilters], responses=JobOfferReadSerializer(many=True))
    def list(self, request: Request) -> Response:
        queryset = offer_services.list_job_offers(active_request_user(request)).select_related(
            "organization"
        )
        queryset = JobOfferFilters(data=request.query_params).apply(queryset)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(JobOfferReadSerializer(page, many=True).data)

    @extend_schema(request=JobOfferCreateSerializer, responses={201: JobOfferReadSerializer})
    def create(self, request: Request) -> Response:
        serializer = JobOfferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer = offer_services.create_job_offer(
            active_request_user(request), serializer.validated_data
        )
        return Response(JobOfferReadSerializer(offer).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        offer = offer_services.get_job_offer(active_request_user(request), pk)
        return Response(JobOfferReadSerializer(offer).data)

    @extend_schema(request=JobOfferUpdateSerializer, responses=JobOfferReadSerializer)
    def update(self, request: Request, pk: UUID) -> Response:
        return self._update(request, pk, partial=False)

    @extend_schema(request=JobOfferUpdateSerializer, responses=JobOfferReadSerializer)
    def partial_update(self, request: Request, pk: UUID) -> Response:
        return self._update(request, pk, partial=True)

    def _update(self, request: Request, pk: UUID, *, partial: bool) -> Response:
        actor = active_request_user(request)
        offer = offer_services.get_job_offer(actor, pk)
        serializer = JobOfferUpdateSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        offer = offer_services.update_job_offer(actor, offer, serializer.validated_data)
        return Response(JobOfferReadSerializer(offer).data)

    @extend_schema(request=JobOfferTransitionSerializer, responses=JobOfferReadSerializer)
    @action(detail=True, methods=["post"])
    def transition(self, request: Request, pk: UUID) -> Response:
        serializer = JobOfferTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer = transition_offer(
            active_request_user(request), pk, serializer.validated_data["status"]
        )
        return Response(JobOfferReadSerializer(offer).data)
