from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.recruitment.api.offer_skills_permissions import IsActiveAuthenticated
from backend.apps.recruitment.api.offer_skills_serializers import (
    OfferSkillCreateSerializer,
    OfferSkillReadSerializer,
    OfferSkillUpdateSerializer,
)
from backend.apps.recruitment.api.query_params import optional_uuid_param
from backend.apps.recruitment.models import OfferSkill
from backend.apps.recruitment.services import offer_skills as offer_skill_services


class OfferSkillViewSet(GenericViewSet[OfferSkill]):
    serializer_class = OfferSkillReadSerializer
    queryset = OfferSkill.objects.none()
    permission_classes = (IsActiveAuthenticated,)

    @extend_schema(
        parameters=[OpenApiParameter("offer_id", UUID, required=False)],
        responses=OfferSkillReadSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        queryset = offer_skill_services.list_offer_skills(
            active_request_user(request),
            offer_id=optional_uuid_param(request, "offer_id"),
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(OfferSkillReadSerializer(page, many=True).data)

    @extend_schema(request=OfferSkillCreateSerializer, responses={201: OfferSkillReadSerializer})
    def create(self, request: Request) -> Response:
        serializer = OfferSkillCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer_skill = offer_skill_services.create_offer_skill(
            active_request_user(request), serializer.validated_data
        )
        return Response(OfferSkillReadSerializer(offer_skill).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        offer_skill = offer_skill_services.get_offer_skill(active_request_user(request), pk)
        return Response(OfferSkillReadSerializer(offer_skill).data)

    @extend_schema(request=OfferSkillUpdateSerializer, responses=OfferSkillReadSerializer)
    def partial_update(self, request: Request, pk: UUID) -> Response:
        actor = active_request_user(request)
        offer_skill = offer_skill_services.get_offer_skill(actor, pk)
        serializer = OfferSkillUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        offer_skill = offer_skill_services.update_offer_skill(
            actor, offer_skill, serializer.validated_data
        )
        return Response(OfferSkillReadSerializer(offer_skill).data)

    def destroy(self, request: Request, pk: UUID) -> Response:
        actor = active_request_user(request)
        offer_skill = offer_skill_services.get_offer_skill(actor, pk)
        offer_skill_services.remove_offer_skill(actor, offer_skill)
        return Response(status=status.HTTP_204_NO_CONTENT)
