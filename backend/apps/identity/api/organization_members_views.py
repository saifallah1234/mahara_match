from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.organization_members_serializers import (
    OrganizationMemberCreateSerializer,
    OrganizationMemberReadSerializer,
    OrganizationMemberUpdateSerializer,
)
from backend.apps.identity.models import OrganizationMember
from backend.apps.identity.services import organization_members as member_services


class OrganizationMemberViewSet(GenericViewSet[OrganizationMember]):
    serializer_class = OrganizationMemberReadSerializer
    queryset = OrganizationMember.objects.none()

    @extend_schema(responses=OrganizationMemberReadSerializer(many=True))
    def list(self, request: Request, organization_id: UUID) -> Response:
        queryset = member_services.list_members(
            request.user,
            organization_id,
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(OrganizationMemberReadSerializer(page, many=True).data)

    def retrieve(
        self,
        request: Request,
        organization_id: UUID,
        user_id: UUID,
    ) -> Response:
        member = member_services.get_member(
            request.user,
            organization_id,
            user_id,
        )
        return Response(OrganizationMemberReadSerializer(member).data)

    @extend_schema(
        request=OrganizationMemberCreateSerializer,
        responses={201: OrganizationMemberReadSerializer},
    )
    def create(
        self,
        request: Request,
        organization_id: UUID,
    ) -> Response:
        serializer = OrganizationMemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        data["organization_id"] = organization_id

        member = member_services.create_member(
            request.user,
            data,
        )

        return Response(
            OrganizationMemberReadSerializer(member).data,
            status=201,
        )

    @extend_schema(
        request=OrganizationMemberUpdateSerializer,
        responses=OrganizationMemberReadSerializer,
    )
    def partial_update(
        self,
        request: Request,
        organization_id: UUID,
        user_id: UUID,
    ) -> Response:
        member = member_services.get_member(
            request.user,
            organization_id,
            user_id,
        )

        serializer = OrganizationMemberUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        member = member_services.update_member(
            request.user,
            member,
            serializer.validated_data,
        )

        return Response(OrganizationMemberReadSerializer(member).data)

    def destroy(
        self,
        request: Request,
        organization_id: UUID,
        user_id: UUID,
    ) -> Response:
        member = member_services.get_member(
            request.user,
            organization_id,
            user_id,
        )

        member_services.remove_member(
            request.user,
            member,
        )

        return Response(status=204)
