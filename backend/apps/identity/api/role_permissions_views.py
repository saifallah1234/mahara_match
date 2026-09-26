from uuid import UUID

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.common_permissions import active_request_user
from backend.apps.identity.api.role_permissions_serializers import (
    RolePermissionCreateSerializer,
    RolePermissionReadSerializer,
)
from backend.apps.identity.models import RolePermission
from backend.apps.identity.services import role_permissions as grant_services


class RolePermissionViewSet(GenericViewSet[RolePermission]):
    serializer_class = RolePermissionReadSerializer
    queryset = RolePermission.objects.none()

    def list(self, request: Request) -> Response:
        queryset = grant_services.list_role_permissions(active_request_user(request))
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(RolePermissionReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        grant = grant_services.get_role_permission(active_request_user(request), pk)
        return Response(RolePermissionReadSerializer(grant).data)

    def create(self, request: Request) -> Response:
        serializer = RolePermissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grant = grant_services.grant_permission(
            active_request_user(request), **serializer.validated_data
        )
        return Response(
            RolePermissionReadSerializer(grant).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request: Request, pk: UUID) -> Response:
        actor = active_request_user(request)
        grant = grant_services.get_role_permission(actor, pk)
        grant_services.revoke_permission(actor, grant)
        return Response(status=status.HTTP_204_NO_CONTENT)
