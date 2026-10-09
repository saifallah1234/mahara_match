from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.organizations_serializers import (
    OrganizationCreateSerializer,
    OrganizationReadSerializer,
    OrganizationUpdateSerializer,
)
from backend.apps.identity.models import Organization
from backend.apps.identity.services import organizations as organization_services


class OrganizationViewSet(GenericViewSet[Organization]):
    serializer_class = OrganizationReadSerializer
    queryset = Organization.objects.none()

    def list(self, request: Request) -> Response:
        queryset = organization_services.list_organizations(request.user)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(OrganizationReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        return Response(
            OrganizationReadSerializer(
                organization_services.get_organization(request.user, pk)
            ).data
        )

    @extend_schema(
        request=OrganizationCreateSerializer, responses={201: OrganizationReadSerializer}
    )
    def create(self, request: Request) -> Response:
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = organization_services.create_organization(
            request.user,
            serializer.validated_data,
        )
        return Response(
            OrganizationReadSerializer(organization).data,
            status=201,
        )

    @extend_schema(request=OrganizationUpdateSerializer, responses=OrganizationReadSerializer)
    def partial_update(self, request: Request, pk: UUID) -> Response:
        organization = organization_services.get_organization(request.user, pk)
        serializer = OrganizationUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        organization = organization_services.update_organization(
            request.user,
            organization,
            serializer.validated_data,
        )
        return Response(OrganizationReadSerializer(organization).data)

    @extend_schema(request=None, responses=OrganizationReadSerializer)
    @action(detail=True, methods=["post"])
    def verify(self, request: Request, pk: UUID) -> Response:
        organization = organization_services.get_organization(request.user, pk)
        organization = organization_services.verify_organization(
            request.user,
            organization,
        )
        return Response(OrganizationReadSerializer(organization).data)

    @extend_schema(request=None, responses=OrganizationReadSerializer)
    @action(detail=True, methods=["post"])
    def reject(self, request: Request, pk: UUID) -> Response:
        organization = organization_services.get_organization(request.user, pk)
        organization = organization_services.reject_organization(
            request.user,
            organization,
        )
        return Response(OrganizationReadSerializer(organization).data)
