from uuid import UUID

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

    def list(self, request: Request, organization_id: UUID) -> Response:
        queryset = member_services.list_members(
            request.user,
            organization_id,
        )
        return Response(
            OrganizationMemberReadSerializer(
                queryset,
                many=True,
            ).data
        )

    def retrieve(
        self,
        request: Request,
        organization_id: UUID,
        pk: UUID,
    ) -> Response:
        member = member_services.get_member(
            request.user,
            organization_id,
            pk,
        )
        return Response(
            OrganizationMemberReadSerializer(member).data
        )

    def create(
        self,
        request: Request,
        organization_id: UUID,
    ) -> Response:
        serializer = OrganizationMemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        data["organization"] = organization_id

        member = member_services.create_member(
            request.user,
            data,
        )

        return Response(
            OrganizationMemberReadSerializer(member).data,
            status=201,
        )

    def partial_update(
        self,
        request: Request,
        organization_id: UUID,
        pk: UUID,
    ) -> Response:
        member = member_services.get_member(
            request.user,
            organization_id,
            pk,
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

        return Response(
            OrganizationMemberReadSerializer(member).data
        )

    def destroy(
        self,
        request: Request,
        organization_id: UUID,
        pk: UUID,
    ) -> Response:
        member = member_services.get_member(
            request.user,
            organization_id,
            pk,
        )

        member_services.remove_member(
            request.user,
            member,
        )

        return Response(status=204)