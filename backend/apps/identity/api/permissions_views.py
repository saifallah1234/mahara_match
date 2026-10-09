from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.identity.api.permissions_serializers import (
    PermissionCreateSerializer,
    PermissionReadSerializer,
)
from backend.apps.identity.models import Permission
from backend.apps.identity.services import permissions as permission_services


class PermissionViewSet(GenericViewSet[Permission]):
    serializer_class = PermissionReadSerializer
    queryset = Permission.objects.none()

    def list(self, request: Request) -> Response:
        queryset = permission_services.list_permissions(request.user)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(PermissionReadSerializer(page, many=True).data)

    def retrieve(self, request: Request, pk: UUID) -> Response:
        permission = permission_services.get_permission(request.user, pk)
        return Response(PermissionReadSerializer(permission).data)

    @extend_schema(request=PermissionCreateSerializer, responses={201: PermissionReadSerializer})
    def create(self, request: Request) -> Response:
        serializer = PermissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        permission = permission_services.create_permission(request.user, serializer.validated_data)
        return Response(
            PermissionReadSerializer(permission).data,
            status=status.HTTP_201_CREATED,
        )
